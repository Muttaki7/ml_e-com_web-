# Production deployment (single VPS, Docker, automatic HTTPS)

This runbook deploys the whole platform on one Linux server:

| Container | Role | Published |
|-----------|------|-----------|
| `caddy` | TLS termination, HTTP→HTTPS redirect, reverse proxy | 80, 443 (TCP+UDP) |
| `frontend` | Next.js storefront + admin UI (standalone) | internal only |
| `backend` | FastAPI API, invoices, uploads (2 workers by default) | internal only |
| `mongodb` | MongoDB 7 replica set `rs0`, auth + keyfile | **not published** |
| `redis` | Shared rate-limit counters, password + AOF | **not published** |

Caddy obtains and renews Let's Encrypt certificates automatically. MongoDB and
Redis are only reachable on the private Compose network.

For a typical small store this runs comfortably on **2 vCPU / 4 GB RAM / 40 GB SSD**.
On a 2 GB server, keep `WEB_CONCURRENCY=1` and `MONGO_WIREDTIGER_CACHE_GB=0.3`.

---

## 1. Server preparation (Ubuntu 22.04 / 24.04)

Create a non-root sudo user (or use your provider's default), then:

```bash
# Updates
sudo apt-get update && sudo apt-get upgrade -y

# Docker Engine + Compose v2 (official convenience script)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker

# Firewall — SSH plus the web ports only
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
```

Do **not** open 27017 (MongoDB) or 6379 (Redis). The Compose file does not publish them.

Install `git`, `curl` and `python3` if your image lacks them:

```bash
sudo apt-get install -y git curl python3
```

### DNS

Pick one:

- **Custom domain (recommended):** create `A` records for the apex host
  (e.g. `shop.example.com`) and `www` (`www.shop.example.com`) pointing at the
  server's public IPv4, or a `CNAME` for `www` pointing at the apex. Add `AAAA`
  only if the server has a working IPv6 address. Wait for DNS to resolve.
- **No domain yet:** use the server's public IP. The env generator turns
  `203.0.113.10` into `203.0.113.10.sslip.io`, a public hostname that resolves to
  that IP and can receive a Let's Encrypt certificate.

Ports 80 and 443 must be reachable from the internet for certificate issuance.

---

## 2. Get the code

```bash
sudo mkdir -p /opt/global-erp
sudo chown "$USER":"$USER" /opt/global-erp
git clone <your-repository-url> /opt/global-erp
cd /opt/global-erp
```

---

## 3. Generate the production environment

```bash
python3 scripts/generate_production_env.py \
  --host shop.example.com \
  --email you@example.com \
  --country US \
  --workers 2
```

Or, without a domain:

```bash
python3 scripts/generate_production_env.py --host 203.0.113.10 --email you@example.com
```

This creates `.env.production` (mode 600) with fresh random secrets for JWT,
MongoDB (root + least-privilege app user), Redis, and payment callbacks. It also
sets `APP_ENV=production`, HTTPS URLs, allowed hosts, and `NEXT_PUBLIC_API_URL=/api/v1`.

Notes:

- **Back up `.env.production`** in a password manager. Losing it means losing the
  database passwords and JWT signing key.
- Never commit it. It is git-ignored.
- Re-running with `--force` rotates every secret; existing database credentials
  remain until MongoDB is reconfigured, so do not rotate casually.
- Custom store country, currency, and branding are configured later in Admin → Settings.
- For domain hosts, the generator also includes `www.<host>` in `SITE_ADDRESS`,
  `ALLOWED_HOSTS`, and `CORS_ORIGINS` so Caddy can issue a certificate for both names.

---

## 4. Deploy

```bash
cd /opt/global-erp
chmod +x scripts/*.sh
./scripts/deploy.sh
```

The script validates the Compose file, builds both images, starts everything,
waits for MongoDB → app user → backend readiness, then checks HTTPS.

Check status and logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f caddy backend
```

The storefront is at `https://<host>/`. The admin login is `https://<host>/admin/login`.

> The first HTTPS check can fail for a minute while Caddy requests the
> certificate. If it never succeeds, see Troubleshooting.

---

## 5. Create the owner account (2FA required)

```bash
cd /opt/global-erp
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli.admin create \
  --email you@example.com --name "Store Owner" --enroll-2fa
```

- You will be prompted for a password (12+ characters).
- Scan the ASCII QR code with Google Authenticator / Authy / 1Password, then enter
  the 6-digit code to activate 2FA.
- **Save the printed backup codes offline.** They are shown once.
- If the session is not interactive, scan the QR, then run
  `... exec backend python -m app.cli.admin enroll-2fa --email you@example.com`
  again to confirm the code.

Useful commands:

```bash
# List admins and whether 2FA is enabled
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli.admin list

# Reset a forgotten admin password
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli.admin reset-password --email you@example.com
```

Do not use `scripts/seed.py` in production: it deletes collections and is blocked
when `APP_ENV=production`. Create categories, products, and staff accounts through
the admin UI.

---

## 6. First-run store setup

Log in at `/admin` and complete:

1. **Settings → Store** — country, currency symbol, timezone, company details,
   delivery charges and free-delivery threshold.
2. **Settings → Banner and Poster Cards** — upload hero/poster photos (max 5 MB
   each, JPEG/PNG/WebP/GIF). Slideshows rotate automatically.
3. **Settings → Payment Methods** — Cash on Delivery is enabled and enforced.
   Card/PayPal/bKash are intentionally disabled until real provider credentials
   are configured and tested; the UI shows them as unavailable.
4. **Catalog** — create categories and products, upload images, set prices/stock.
5. **Staff** — create additional admin accounts with least-privilege roles. Every
   admin requires TOTP 2FA.
6. Place a test COD order end to end; confirm stock decreases and invoices appear
   under `/uploads/invoices/`.

---

## 7. Operations

### Update a deployment

```bash
cd /opt/global-erp
./scripts/backup_mongo.sh        # take a backup first
git pull
./scripts/deploy.sh
```

Schemaless MongoDB means there are no migrations. Existing data and uploads stay
in Docker volumes across rebuilds.

### Backups

```bash
./scripts/backup_mongo.sh
# -> backups/mongo-20261025T031500Z.archive.gz (git-ignored)
```

Daily cron example (03:15 UTC, keep 14 days):

```cron
15 3 * * * cd /opt/global-erp && BACKUP_DIR=/var/backups/global-erp ./scripts/backup_mongo.sh >> /var/log/global-erp-backup.log 2>&1
```

Copy backups off the server (S3, Backblaze, another host). A backup that only
exists on the same VPS is not a backup. Uploaded images live in the
`uploads_data` Docker volume; back it up too if you need full disaster recovery:

```bash
docker run --rm -v global-erp_uploads_data:/data -v "$PWD/backups:/backup" \
  alpine tar czf /backup/uploads-$(date -u +%Y%m%dT%H%M%SZ).tar.gz -C /data .
```

### Restore

```bash
./scripts/restore_mongo.sh backups/mongo-20261025T031500Z.archive.gz
```

The script stops the backend, drops/replaces the app database, and restarts the
backend. It asks for confirmation; add `--yes` for automation.

### Logs and health

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
curl -fsS https://<host>/health        # liveness
curl -fsS https://<host>/health/ready  # MongoDB + Redis reachability
```

Application logs are JSON in Caddy's stdout and structured logs from the backend
(`docker compose ... logs backend`). Docker rotates logs at 10 MB × 3 per container.

### Restart / stop

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml restart backend
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

### Change the domain

Edit `SITE_ADDRESS`, `ALLOWED_HOSTS`, `FRONTEND_URL`, and `CORS_ORIGINS` in
`.env.production` (all four must use the new host), point DNS at the server, then:

```bash
./scripts/deploy.sh
```

Caddy retains old certificates in `caddy_data` but serves only the configured host.

---

## 8. Email (optional)

Order confirmation emails are disabled while `SMTP_HOST` is empty; checkout still
works. To enable them, set the `SMTP_*` values in `.env.production` and redeploy:

```dotenv
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM=Your Shop <no-reply@example.com>
SMTP_STARTTLS=true
SMTP_SSL=false
SUPPORT_EMAIL=support@example.com
```

Then `./scripts/deploy.sh` (or `... up -d backend`). Email failures are logged and
never fail an order.

---

## 9. Security checklist

- [ ] SSH keys only; password login disabled; firewall allows 22/80/443 only.
- [ ] MongoDB and Redis not published to the host.
- [ ] `.env.production` mode 600, backed up offline, never committed.
- [ ] Admin 2FA enrolled; backup codes stored offline.
- [ ] Demo seed not run; test accounts removed.
- [ ] COD verified end to end; online gateways left off until credentials and
      callbacks are tested.
- [ ] Automatic backups plus off-server copies.
- [ ] Server security updates applied (`unattended-upgrades`) and rebooted when needed.
- [ ] GitHub CI green on `main`.

---

## 10. Troubleshooting

| Symptom | Check |
|---------|-------|
| Caddy logs `no such host` / ACME failure | DNS A record points at this server; ports 80/443 open; `SITE_ADDRESS` has no `https://` prefix. |
| `backend` restarts with `Unsafe production configuration` | `.env.production` is missing required production values; regenerate it instead of hand-editing. |
| `backend` unhealthy, `mongo-init` failed | `docker compose ... logs mongodb mongo-init`. Passwords may contain characters outside `[A-Za-z0-9]`, or the data volume has old credentials. |
| 502 from Caddy | `docker compose ... logs backend`; wait for the first build/start; confirm `/health/ready` inside the container. |
| Cannot log in as admin | Confirm 2FA enrollment is complete (`admin list` shows `2fa=yes`); reset password with the CLI; check server clock (TOTP requires accurate time). |
| Uploads disappear after redeploy | `uploads_data` volume must remain; do not run `down -v`. |
| Certificate rate limit on `*.sslip.io` | Move to a real domain with a `SITE_ADDRESS` change and redeploy. |

---

## 11. Stack layout

```
docker-compose.prod.yml        production services, networks, volumes
infrastructure/Caddyfile       TLS, routing, security headers, request limit
infrastructure/mongo/          replica-set + app-user bootstrap
scripts/generate_production_env.py
scripts/deploy.sh              build/start/wait/verify
scripts/backup_mongo.sh        mongodump + retention
scripts/restore_mongo.sh       mongorestore
.github/workflows/ci.yml       compile, typecheck/build, compose validation
```

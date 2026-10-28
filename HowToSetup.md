# How to Set Up GlobalShop

This guide takes a clean checkout to a running storefront, API, and ERP admin on your machine. For a public server use [DEPLOYMENT.md](DEPLOYMENT.md); for the free Vercel + Render path use [FREE_HOSTING.md](FREE_HOSTING.md).

The same codebase serves one store in any country. Country, currency, delivery charges, branding, and payment methods are configuration, not code.

## 1. Prerequisites

| Tool | Minimum | Notes |
|------|---------|-------|
| Python | 3.11+ (3.12 recommended) | Backend API, CLI, tests |
| Node.js | 20+ (24 LTS recommended) | Next.js frontend |
| MongoDB | 7.x | Local Docker container or MongoDB Atlas |
| Redis | 7.x | Optional for local development; required in production for shared rate limits |
| Docker | 24+ | Optional, for MongoDB or the bundled stack |

Ports used locally:

- `3000` — Next.js storefront and admin
- `8000` — FastAPI and OpenAPI docs
- `27017` — MongoDB

## 2. Start MongoDB

Local Docker (development only, no authentication):

```bash
docker run -d --name globalshop-mongo -p 27017:27017 mongo:7
```

Or use MongoDB Atlas: create a free M0 cluster, create a database user, add your current IP to the allowlist, and copy the connection string.

The local default database name is `global_ecommerce_erp` (see `backend/.env.example`).

## 3. Install and start the backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Windows Git Bash
source .venv/Scripts/activate

# macOS or Linux
source .venv/bin/activate
```

Install dependencies and create the environment file:

```bash
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Edit `backend/.env` if your MongoDB is not on `mongodb://localhost:27017`. Generate a real secret for anything beyond local development:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Start the API:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check it:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
```

Interactive API docs are available at http://127.0.0.1:8000/docs in development. They are intentionally disabled when `APP_ENV=production`.

## 4. Seed demo data (local only)

```bash
cd backend
python ../scripts/seed.py
```

The demo seed creates one Main Admin, one inventory manager, 19 categories, 12 product templates (some with variants), 80 customers, and 90 days of orders so analytics and ML pages have data.

Demo sign-ins:

- Main Admin: `admin@example.com` / `Admin@12345`
- Inventory manager: `robin@example.com` / `Robin@12345`
- Customers: `customer1@example.com` ... `customer80@example.com` / `Customer@123`

> These are local demo credentials. Change the passwords and enroll 2FA before exposing the app to the internet.

> The seed script deletes collections. It refuses to run when `APP_ENV=production` or when `MONGODB_URI` points at a remote host, unless `ALLOW_REMOTE_SEED=1` is set. Only override that guard for a disposable database.

## 5. Install and start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

`frontend/.env.development` already points the browser at `http://localhost:8000/api/v1`. If your API runs elsewhere, set:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

`NEXT_PUBLIC_*` values are compiled into the frontend, so restart or rebuild after changing them.

Open:

- Landing page: http://localhost:3000
- Storefront: http://localhost:3000/shop
- Admin ERP: http://localhost:3000/admin/login

For a public demo, set `DEMO_MODE=true` before starting the backend; the login
pages then show **Login as Admin** / **Login as User** and the bootstrap creates
the demo accounts. Leave it unset for a real store.

## 6. First admin login and branding

### First admin login

After the local seed, sign in at http://localhost:3000/admin/login with `admin@example.com` / `Admin@12345`, then change that password before exposing the app:

```bash
cd backend
python -m app.cli.admin reset-password --email admin@example.com
```

In production, create the owner account when the stack is running. The `--enroll-2fa` flag prints a TOTP secret and backup codes once; store them offline:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli.admin create \
  --email owner@example.com --name "Store Owner" --enroll-2fa
```

For the hosted path, set `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` (16+ random characters), and `BOOTSTRAP_ADMIN_NAME` on the backend service; the account is created on startup when it does not exist. Remove the bootstrap password after the first successful login.

### Branding and store localization

Most branding is configuration, not code. Sign in to the admin ERP, open **Settings**, change the values, and save:

- **Store Country & Currency** — country, currency, currency symbol, and timezone. These drive prices, delivery rates, and invoice dates.
- **Company & Invoice Details** — company name, support email, support phone, and registered address shown on invoices and the storefront footer.
- **Homepage Poster & Banner** — hero photos (auto-slideshow) plus badge, title, and subtitle.
- **Poster Cards** — per-card images and visible/hidden state, with their own slideshows.
- **Delivery Pricing** — local and international charges, plus an optional free-delivery threshold.
- **Payment Methods** — enable only methods that are implemented and tested. Cash on Delivery is the supported method; online gateways stay disabled until their credentials and signed callbacks are verified.

The static brand strings live in the frontend source and can be changed in a fork:

| Location | String |
|----------|--------|
| `frontend/app/layout.tsx` | Browser title and meta description |
| `frontend/components/Footer.tsx` | Footer wordmark |
| `frontend/app/register/page.tsx` | Registration welcome text |
| `frontend/app/products/[id]/page.tsx` | Fallback brand when a product has no brand |

Product brand names are per-product fields, edited on **Admin > Products**.

## 7. Docker development stack (optional)

The bundled development compose file starts MongoDB, Redis, the API, and the frontend:

```bash
docker compose up --build
```

Then seed data against the compose database from the host:

```bash
cd backend
python ../scripts/seed.py
```

The development compose database name and the local `.env` default both use `global_ecommerce_erp`.

## 8. Verify the installation

```bash
# Backend health
curl http://127.0.0.1:8000/health/ready

# Enforce 2FA regression suite (in-memory database, no MongoDB needed)
cd backend
python ../scripts/test_2fa_flows.py

# Live security smoke test (backend, MongoDB, and demo seed must be running)
python ../scripts/security_smoke.py

# Frontend type check, lint, and production build
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

In the browser:

1. Open the storefront and confirm products and images render.
2. Sign in to the admin ERP with the seeded Main Admin.
3. Open **Admin > Settings > Two-factor authentication**, enroll TOTP, and save the backup codes.
4. Place a Cash on Delivery test order with a customer account.
5. In the admin ERP, move the order through `confirmed`, `shipped`, and `delivered`; confirm stock is committed and the invoice downloads.
6. Sign out and back in; the admin account should now ask for the 6-digit TOTP code.

## 9. Environment variables

Backend (`backend/.env`):

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development` or `production`. Production enables strict config checks. |
| `DEBUG` | Must be `false` in production. |
| `SECRET_KEY` | JWT signing key. Generate a long random value. |
| `MONGODB_URI` | MongoDB connection string. |
| `MONGODB_DB` | Database name. Default: `global_ecommerce_erp`. |
| `REDIS_URL` | Shared rate-limit storage. Required in production. |
| `FRONTEND_URL` | Public storefront origin; also added to CORS automatically. |
| `CORS_ORIGINS` | Comma-separated allowed browser origins. |
| `ALLOWED_HOSTS` | Comma-separated API hostnames. Required in production. |
| `TRUST_PROXY_HEADERS` | Set `true` only behind a proxy that overwrites `X-Real-IP` / `X-Forwarded-For`. |
| `UPLOAD_ROOT` | Uploaded image and invoice directory. Use persistent storage in production. |
| `STORE_COUNTRY`, `CURRENCY`, `CURRENCY_SYMBOL`, `TIMEZONE` | Initial storefront defaults; admins can override them in Settings. |
| `PAYMENT_CALLBACK_SECRET` | HMAC secret for payment callbacks. Generate a random value. |
| `STRIPE_*`, `PAYPAL_*` | Online gateway credentials. Leave empty until the gateways are tested. |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME` | One-time hosted admin bootstrap. |
| `BOOTSTRAP_DEMO_DATA` | `true` inserts a small demo catalog when the products collection is empty. |

Frontend:

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | API base URL. Use `/api/v1` for same-origin Caddy/Docker deployments, or an absolute URL when the API is on another host. |

Never commit `.env`, `.env.production`, `.env.local`, or real credentials. The repository ignores them.

## 10. Production deployment

### Single VPS (recommended for full control)

Follow [DEPLOYMENT.md](DEPLOYMENT.md). In short:

```bash
python3 scripts/generate_production_env.py --host shop.example.com --email you@example.com
./scripts/deploy.sh
docker compose --env-file .env.production -f docker-compose.prod.yml \
  exec backend python -m app.cli.admin create --email you@example.com --name "Store Owner" --enroll-2fa
```

Caddy terminates HTTPS and serves the storefront, API, and uploads from one origin. MongoDB and Redis stay on the private Docker network.

### Free staging (Vercel + Render + Atlas)

Follow [FREE_HOSTING.md](FREE_HOSTING.md). Summary:

1. Create an Atlas M0 cluster and allow Render egress (`0.0.0.0/0`) or a fixed egress range.
2. Deploy the Render Blueprint (`render.yaml`); set `MONGODB_URI`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, and the URLs.
3. Deploy `frontend/` to Vercel with `NEXT_PUBLIC_API_URL=https://<render-service>.onrender.com/api/v1`.
4. Set Render `FRONTEND_URL` and `CORS_ORIGINS` to the Vercel URL, then redeploy.

Free-tier caveats: the Render service sleeps after inactivity, its disk is ephemeral (uploaded files and generated invoices can disappear), Atlas M0 is small, and Vercel Hobby is for non-commercial use.

## 11. Common problems

| Symptom | Cause and fix |
|---------|----------------|
| `ServerSelectionTimeoutError` | MongoDB is not running or the URI is wrong. Start the container and check `MONGODB_URI`. For Atlas, check the IP allowlist. |
| Browser reports CORS errors | Add the exact frontend origin to `CORS_ORIGINS` and set `FRONTEND_URL`. Include scheme and port; no trailing slash. |
| Admin API returns 401 | Use the admin login route and an admin token. Customer tokens cannot access admin routes. |
| Login returns 423 | Account lockout after repeated failures. Wait `LOCKOUT_MINUTES` or reset the password with the admin CLI. |
| Login returns 429 | Rate limit reached. Wait for the window to reset; check Redis in production. |
| Images work locally, 404 on Vercel + Render | Set `NEXT_PUBLIC_API_URL` to the absolute Render API URL and rebuild the frontend. The storefront resolves `/uploads/*` through `mediaUrl()`. |
| Uploaded image disappears on Render | Render free disk is ephemeral. Use persistent object storage for production uploads. |
| Seed exits with "Refusing to seed" | The database is remote or `APP_ENV=production`. Use a local database; override only for disposable environments. |
| Invoice download fails on free hosting | Generated invoices live under `UPLOAD_ROOT`. Request the invoice through the authenticated API rather than a static file URL. |
| Lost admin 2FA device | Use a saved backup code. A Main Admin can reset another admin's 2FA with `POST /api/v1/admins/{id}/2fa/reset`. |
| Forgot admin password | From `backend/`: `python -m app.cli.admin reset-password --email you@example.com` |
| Port already in use | Stop the conflicting process or run Next.js on another port and update CORS/`FRONTEND_URL` accordingly. |

## 12. Security checklist before going public

- Change every demo password; never seed a production database.
- Enroll TOTP 2FA for every admin and store backup codes offline.
- Set a long random `SECRET_KEY` and `PAYMENT_CALLBACK_SECRET`.
- Run with `APP_ENV=production`, `DEBUG=false`, HTTPS, Redis, and explicit `ALLOWED_HOSTS`.
- Leave online payment gateways disabled until their credentials and signed callbacks are verified end to end.
- Keep MongoDB private; restrict Atlas access to known networks where possible.
- Back up MongoDB and uploads off the server, and test restoring them.
- Review [DEPLOYMENT.md](DEPLOYMENT.md) for the full launch checklist.

## 13. Documentation

- [README.md](README.md) — architecture, features, API groups, performance notes
- [DEPLOYMENT.md](DEPLOYMENT.md) — production VPS runbook
- [FREE_HOSTING.md](FREE_HOSTING.md) — Vercel + Render + Atlas free-tier runbook
- [AGENTS.md](AGENTS.md) — repository guide for contributors and coding agents
- [CHANGELOG.md](CHANGELOG.md) — release history
- [database/schema.sql](database/schema.sql) — SQL-readable reference of the MongoDB document model
- [database/seed.sql](database/seed.sql) — demo catalog and storefront settings for the reference schema

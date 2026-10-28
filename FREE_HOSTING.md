# Free hosting: Vercel + Render + MongoDB Atlas

This is the **zero-cost demo/staging path**: the Next.js storefront runs on Vercel,
the FastAPI backend on Render (Docker), rate-limit storage on Render Key Value,
and MongoDB on Atlas M0.

For a real, always-on store use the single-VPS stack in [DEPLOYMENT.md](DEPLOYMENT.md)
or paid managed services. The free tiers below have hard limits that make them
unsuitable for actual sales at scale — see [Limitations](#limitations).

```
Browser
  ├── https://<project>.vercel.app      Next.js (Vercel Hobby)
  └── https://<service>.onrender.com    FastAPI (Render free, Docker)
          ├── MongoDB Atlas M0 (database)
          └── Render Key Value (rate limiting)
```

## What Render's free tier cannot do

- **No shell / no one-off jobs** — the admin account and demo catalog are created
  automatically at container start from `BOOTSTRAP_*` environment variables.
- **No persistent disk** — uploaded images and generated invoices live in
  `/tmp/uploads` and disappear on every restart or redeploy. Demo product art is
  an inline SVG stored in MongoDB, so it survives. For real media, use a paid
  Render disk or object storage.
- **Spins down after 15 minutes idle** — the first request afterwards can take
  30–60 seconds (cold start).
- **512 MB RAM / 0.1 CPU, one instance** — enough for a demo, not for production
  traffic. The blueprint sets `WEB_CONCURRENCY=1` to fit.

> Vercel **Hobby is for non-commercial use only**. A live store needs Vercel Pro,
> or self-host the frontend. The Render free plan is likewise a preview tier.

## 0. Prerequisites

- A GitHub repository containing the current code. The deployment files are
  `render.yaml`, `frontend/vercel.json`, `backend/Dockerfile` and
  `backend/app/cli/bootstrap.py`.
- Free accounts on [MongoDB Atlas](https://cloud.mongodb.com),
  [Render](https://render.com) and [Vercel](https://vercel.com), all connected
  to that GitHub repository.
- Nobody should reuse the existing production Atlas cluster for this. Create a
  **dedicated** free cluster.

## 1. MongoDB Atlas (free M0)

1. Create a project and an **M0** cluster. Pick AWS **Oregon (`us-west-2`)** to
   match the Render region; any region works, but keep them close.
2. **Database Access → Add New Database User**: username `globalshop`, a long
   random password (save it), role *Read and write to any database*.
3. **Network Access → Add IP Address**: `0.0.0.0/0` with a comment such as
   `Render free egress`. Render's free outbound IPs are not static, so the
   database must accept connections from anywhere. Protect it with the strong
   password; for IP allowlisting, move to a paid Render plan with static
   outbound IPs.
4. Copy the SRV connection string:
   `mongodb+srv://globalshop:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   URL-encode special characters in the password (`@` → `%40`, `:` → `%3A`,
   `/` → `%2F`, `#` → `%23`).

Do not change the allowlist or credentials of an existing production cluster.

## 2. Render backend (Blueprint)

1. Push the current code to the GitHub branch you will deploy.
2. Render Dashboard → **New → Blueprint** → connect the repository. Render reads
   `render.yaml` and proposes:
   - web service `globalshop-api` (Docker, `backend/`, free)
   - Key Value `globalshop-rate-limit` (free)
3. Fill the prompted (`sync: false`) values:

   | Variable | Value |
   |---|---|
   | `MONGODB_URI` | Atlas SRV URL from step 1 |
   | `FRONTEND_URL` | `https://placeholder.vercel.app` for now (must be HTTPS) |
   | `CORS_ORIGINS` | same placeholder |
   | `BOOTSTRAP_ADMIN_EMAIL` | your admin email |
   | `BOOTSTRAP_ADMIN_PASSWORD` | **16+ random characters** (minimum 12) |

   Everything else (secrets, Mongo database name, allowed host, pool size,
   `/tmp/uploads`, demo catalog) is already set in the blueprint.

   For a public demo, also set `DEMO_MODE=true` in the Render dashboard. That
   seeds a demo admin and demo shopper and shows **Login as Admin** / **Login as
   User** on the login pages. Leave it `false` for anything with real data.
   `scripts/generate_production_env.py --demo` does the same for the Docker stack.
4. **Apply**. The first Docker build downloads the Python/ML wheels and can take
   10–20 minutes. The service only becomes live once `/health/ready` returns
   200 — that endpoint checks both MongoDB and Key Value.
5. If the deploy fails, open the service logs. The usual causes are:
   - Atlas network allowlist not yet applied (`0.0.0.0/0`);
   - special characters in the Atlas password not URL-encoded;
   - the database user lacking read/write permission.
6. Copy the public URL, e.g. `https://globalshop-api.onrender.com`. Check:
   - `https://<service>.onrender.com/health` → `{"status":"ok"}`
   - `https://<service>.onrender.com/api/v1/products` → 12 demo products

On first boot the entrypoint creates the Main Admin (if missing) and inserts a
12-product demo catalog with inline SVG images. It never deletes data and never
overwrites an existing admin or non-empty catalog.

If Render had to choose a different service name, `RENDER_EXTERNAL_HOSTNAME` is
added to the allowed hosts automatically. Update `ALLOWED_HOSTS` only when you
add a custom domain.

## 3. Vercel frontend

1. Vercel → **Add New → Project** → import the same repository.
2. **Root Directory:** `frontend`. Framework preset: **Next.js** (auto-detected).
   Leave build/output settings at their defaults.
3. Environment variable for **Production** (and Preview if you use it):
   ```
   NEXT_PUBLIC_API_URL=https://<service>.onrender.com/api/v1
   ```
   Include `/api/v1`; no trailing slash. This value is **baked into the build**,
   and the Content-Security-Policy is generated from it — changing it requires a
   new deployment.
4. Deploy and copy the production URL, e.g. `https://globalshop.vercel.app`.
   Preview deployment URLs (`*-git-*.vercel.app`) have different origins and are
   not covered by CORS.

## 4. Connect the two (CORS) — required

In Render → `globalshop-api` → **Environment**, replace the placeholders:

```
FRONTEND_URL = https://globalshop.vercel.app
CORS_ORIGINS = https://globalshop.vercel.app
```

No trailing slash. Save; Render redeploys automatically. Multiple origins are
comma-separated. The backend also appends `FRONTEND_URL` to CORS, so both
variables should normally match.

Then verify from the Vercel site:

- homepage lists products and product images load;
- product detail, cart and COD checkout work;
- `/admin/login` loads and can authenticate.

If images at `/uploads/...` 404, the API URL was relative or missing `/api/v1`;
`mediaUrl()` resolves backend-relative upload paths against the API origin, but
only when `NEXT_PUBLIC_API_URL` is an absolute URL at build time.

## 5. First admin login and hardening

1. Open `https://<project>.vercel.app/admin/login` and sign in with the
   `BOOTSTRAP_ADMIN_*` credentials.
2. Open **Admin → Settings → Two-Factor Authentication** and enroll an
   authenticator app. Until enrollment the account is protected by the password
   only. Store the backup codes; there is no self-service reset.
3. Confirm the store settings: currency, store country, delivery charges,
   slideshow images, COD-only payments.
4. In Render, **delete both** `BOOTSTRAP_ADMIN_EMAIL` and
   `BOOTSTRAP_ADMIN_PASSWORD` environment variables (or empty the email). The
   existing admin is left untouched. Keep `BOOTSTRAP_DEMO_DATA` or set it to
   `false`; it only seeds when the products collection is empty.
5. Save the final admin credentials in a password manager.

Never expose the bootstrap password, `SECRET_KEY` or `PAYMENT_CALLBACK_SECRET`.
`render.yaml` generates the last two automatically.

## 6. Custom domains (optional)

- **Frontend:** add the domain in Vercel → Project → Domains, then update
  `FRONTEND_URL` and `CORS_ORIGINS` in Render and let it redeploy.
- **Backend:** add the domain to Render and to `ALLOWED_HOSTS`, then update
  `NEXT_PUBLIC_API_URL` in Vercel and redeploy the frontend (the value is baked
  into the client bundle).
- HTTPS certificates are automatic on both platforms.

## Limitations

| Area | Free-tier behaviour | Production move |
|---|---|---|
| Vercel | Hobby is non-commercial; serverless request limits | Vercel Pro or self-host |
| Render web | Sleeps after 15 min idle; 512 MB / 0.1 CPU; 750 h/month | Starter/Standard plan, always-on |
| Render disk | Ephemeral `/tmp/uploads`; media lost on restart | Paid disk or S3/R2 media storage |
| Render shell | Unavailable; only startup bootstrap | Paid plan or VPS |
| Key Value | Free, non-persistent; rate-limit counters reset | Paid Key Value |
| Atlas M0 | 512 MB, shared RAM, connection limits, no continuous backups | M10+ with backups |
| Email | `SMTP_*` unset → order emails skipped | Configure SMTP |
| Payments | COD only (no gateway credentials) | Configure and test gateways |

This stack is appropriate for a public **demo/staging** site. For the 30k-user
backend target, use the Docker/VPS production stack (Caddy + Mongo replica set +
Redis + backups) or paid managed equivalents, with media on object storage and
Vercel Pro/self-hosting for the frontend.

## Troubleshooting

- **Render health check 503/timeout:** check Atlas allowlist and credentials,
  then the Key Value link. `/health/ready` reports `mongodb` and `redis`.
- **CORS errors in the browser:** `FRONTEND_URL`/`CORS_ORIGINS` must exactly
  match the page origin (scheme + host, no path, no trailing slash), and the
  backend must have redeployed.
- **API calls go to Vercel/404:** `NEXT_PUBLIC_API_URL` is missing or relative.
  Set the absolute Render URL + `/api/v1`, then redeploy the frontend.
- **Images disappear after a while:** expected with ephemeral Render storage;
  re-upload to a paid disk/object store.
- **First request slow:** free Render service waking from sleep.
- **Admin locked out:** 5 failed logins lock the account for 15 minutes;
  wait or reset it from the database.

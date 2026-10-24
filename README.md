# Global Commerce + ERP + Machine Learning Platform

Production-oriented monorepo for e-commerce businesses operating in **any country** — single store, configured by admin settings (no code changes needed per deployment).

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React, TypeScript, Tailwind CSS, Recharts |
| Backend | Python 3.12, FastAPI, Pydantic v2, Motor (async MongoDB) |
| Database | MongoDB (local or Atlas) |
| Auth | Separate Customer vs Admin JWT, TOTP 2FA (admins + customers), RBAC, audit logs |
| Payments | COD, Stripe (card), PayPal — plus bKash / Nagad / Rocket adapters for Bangladesh deployments |
| ML | Demand forecast, Product Intelligence Score, smart purchase recommendations |
| Infra | Docker Compose, Nginx-ready |

## Quick start

### 1. MongoDB
```bash
docker run -d -p 27017:27017 --name mongo mongo:7
# or use Atlas and set MONGODB_URI
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Seed demo data
```bash
cd backend
python ../scripts/seed.py
```
- **Main Admin**: `admin@example.com` / `Admin@12345`
- **Customers**: `customer1@example.com` … `customer10@example.com` / `Customer@123`

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
- Storefront: http://localhost:3000
- Admin ERP: http://localhost:3000/admin/login

### 5. Docker (all services)
```bash
docker compose up --build
```

## Going global — one store, any country

Everything is driven by **Admin → Settings** (`GET/PATCH /api/v1/settings`), stored in MongoDB and used across the platform:

- **Store country** — pick from 223 countries. The store currency, currency symbol, and timezone sync from the country data automatically (overridable). Domestic vs international delivery charges are computed by comparing the customer's shipping country to the store country.
- **Currency** — orders persist the store currency at checkout time; prices display via `Intl.NumberFormat`. Invoices use the order's currency.
- **Phone numbers** — strict E.164 everywhere (validated server-side with libphonenumber). The frontend provides a dial-code selector per country.
- **Addresses** — `{ country, state?, city, address_line, postal_code? }`, country validated against ISO 3166-1.
- **Payment methods** — enable/disable COD, Card (Stripe), PayPal, bKash, Nagad, Rocket per deployment. Checkout and the payment-initiate endpoint both enforce the enabled list.
- **Branding** — store name, banner copy, company/invoice details (name, address, phone, email, tax ID) are all settings-driven.
- **Homepage slideshows** — under **Admin → Settings**, upload up to 12 photos for the hero poster and up to 12 for each poster card. The hero auto-advances every 6 seconds and cards every 5 seconds; sections without photos keep their gradient background. Photos are validated as real JPEG/PNG/WebP/GIF files (5 MB max) and stored under `/uploads/site/`.

Environment defaults live in `backend/.env` (`STORE_COUNTRY`, `CURRENCY`, `TIMEZONE`, `ORDER_NUMBER_PREFIX`, plus `STRIPE_*` / `PAYPAL_*` when card/PayPal are enabled).

`GET /api/v1/settings/meta/countries` exposes the country list (code, name, dial code, currency) to the frontend.

## Two-factor authentication (proper)

Both admins and customers support TOTP (Google Authenticator etc.) with backup codes:

1. **Password step** — on success with 2FA enabled, the API returns a **challenge**: a short-lived (5 min) temp token carrying a `2fa_pending` claim. No session is opened yet.
2. **Verify step** — `POST /auth/*/2fa/verify` sends `{ temp_token, code }`. The temp token's `jti` is stored on the account (`pending_2fa`), so:
   - the challenge is **bound to the completed password step** (a verify call without a matching temp token is rejected),
   - the challenge is **single-use** (consumed after success — replay is rejected),
   - it **expires** independently of the final access token,
   - **per-account attempt lockout**: 5 failures lock the account for 15 minutes (`MAX_2FA_ATTEMPTS`, `LOCKOUT_MINUTES` in settings).
3. **Backup codes** — 8-char codes, bcrypt-hashed at rest, single-use (burned on success).
4. **Enrollment** — `2fa/setup` → returns secret + QR (base64 PNG) + backup codes (shown once) → `2fa/confirm` with a valid TOTP code activates it. `2fa/disable` requires a TOTP or backup code. Admin enrollment is available under **Admin → Settings → Security**; customer 2FA is opt-in (managed under **My Account**). Once an account is enrolled, every login requires the second factor. The seeded demo admin is intentionally left unenrolled so the demo can be opened; enroll all real admin accounts before go-live.
5. After successful verification, normal access + refresh JWTs are issued (type-claim enforced: customer tokens never work on admin routes and vice versa).
6. **Attempt lockout is account-level** — five bad codes set `two_factor_locked_until` on the account, so restarting the password step cannot reset the attempt budget.

End-to-end regression test (fake in-memory DB, no MongoDB required):

```bash
cd backend
./.venv/Scripts/python.exe ../scripts/test_2fa_flows.py
```

Live security smoke test (requires the backend, MongoDB and demo data running):

```bash
cd backend
./.venv/Scripts/python.exe ../scripts/security_smoke.py
```

## Security model

- Customer tokens never work on admin routes (token `type` claim enforced).
- **Refresh tokens cannot be used as access tokens**: the bearer dependencies reject the `token_use=refresh` claim. Refresh tokens are rotated on use and revoked on logout (`POST /auth/customer/logout` or `/auth/admin/logout` with `{ "refresh_token": "..." }`).
- Admin login: email → password → 2FA challenge (when enrolled) → JWT with role + permissions.
- Main Admin has all permissions and cannot be disabled/deleted by normal admins.
- Lower admins cannot escalate their own role or create Main Admin.
- Login lockout (5 attempts / 15 min) on password and 2FA steps; login timing is equalized for unknown emails.
- Auth endpoints are rate-limited with slowapi (per process; use a shared store or edge limiter when running many instances).
- `get_client_ip` ignores `X-Forwarded-For` unless `TRUST_PROXY_HEADERS=true`, which must only be set behind a proxy that overwrites the header.
- **Payment callbacks are authenticated**: `/payments/{provider}/callback` requires an `X-Payment-Signature: sha256=<HMAC-SHA256(raw body, PAYMENT_CALLBACK_SECRET)>` header (or a valid `Stripe-Signature` for card callbacks when `STRIPE_WEBHOOK_SECRET` is set). Provider, order method and amount must match; paid orders cannot be downgraded; callbacks are rejected when no secret is configured.
- Product image uploads validate magic bytes and force the stored extension from the detected JPEG/PNG/WebP/GIF type (filename and declared MIME are not trusted).
- Checkout reserves stock atomically; cancellations release reservations and deliveries commit them, with idempotency flags.
- Every sensitive action is written to `audit_logs`.
- API responses set `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy`; the Next.js frontend sets the equivalent browser headers.
- In production (`DEBUG=false`) the API refuses to start with the default or a short `SECRET_KEY`.

Recommended before a public launch: enroll 2FA on every admin account, terminate TLS at the proxy/CDN, restrict `/uploads` and `/docs` at the edge if they are not needed publicly, and move rate-limit counters to Redis when running more than one API instance.

## Performance & scaling

The API runs on FastAPI/Uvicorn; for production use multiple workers and turn off
per-request access logging:

```bash
cd backend
DEBUG=false .venv/Scripts/python.exe -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --workers 4 --no-access-log
```

On Linux/macOS use `.venv/bin/uvicorn` instead. Set `DEBUG=false` in `.env` for
deployments (request logs are then only written for 4xx/5xx responses).

Measured on a 6-core AMD Ryzen 5 laptop with 15 GB RAM, MongoDB on localhost, the
production Next.js server, and Node.js as the load generator (concurrency in
parentheses, zero failed requests):

| Target | Throughput | p95 latency |
|--------|-----------|-------------|
| `GET /health`, 4 Uvicorn workers (100) | ~4,290 req/s | 36 ms |
| `GET /api/v1/settings/public`, 4 workers (100) | ~1,395 req/s | 131 ms |
| `GET /api/v1/products?limit=20`, 4 workers (100) | ~1,264 req/s | 101 ms |
| `GET /api/v1/meta/countries`, 4 workers (100) | ~840 req/s | 172 ms |
| Customer login (bcrypt), 4 workers (20) | ~30 req/s | 923 ms |
| Storefront `/` (Next production server, 100) | ~1,200 req/s | 99 ms |
| Storefront `/products` (Next production server, 100) | ~1,730 req/s | 65 ms |

Reproduce with:

```bash
node scripts/load_test.js --port 8000 --path /health --concurrency 200 --duration 10
node scripts/load_test.js --port 8000 --path "/api/v1/products?limit=20" --concurrency 200
node scripts/load_test.js --port 8000 --method POST --path /api/v1/auth/customer/login \
  --body '{"email":"customer1@example.com","password":"Customer@123"}' --concurrency 20
```

What this means for large audiences:

- **Frontend:** Next.js prerenders `/` and `/products` with
  `Cache-Control: s-maxage=31536000`; static assets are `immutable`. Put the
  frontend behind a CDN (Cloudflare/Vercel/CloudFront). The CDN serves the billion
  users; the Next.js origin only handles cache misses. No single machine can
  verify a billion users — plan capacity with the CDN provider and origin shielding.
- **30,000 concurrent backend users:** at one request every 30 s that is ~1,000
  req/s, close to one 4-worker node's measured read capacity. Deploy at least two
  API nodes behind a load balancer, use a MongoDB replica set, and add Redis for
  hot reads (settings, catalog), sessions, and shared rate limiting. Add a
  `slowapi`/gateway rate limit — the limiter is configured but not yet applied to
  routes.
- **Login bursts:** bcrypt is CPU-bound (~26 logins/s per 6-core node). A 30,000-user
  login burst spread over an hour needs ~8 req/s (fits one node); compressed into
  five minutes it needs ~100 req/s, i.e. 4+ app nodes or a waiting-room/queue.
- **MongoDB:** run a replica set with a connection-pool size tuned per worker
  (`maxPoolSize` currently defaults to 100 per process), and keep the TTL index on
  `refresh_tokens` (already created) plus indexes on order/customer fields.
- **Writes:** these figures cover reads and logins. Checkout and inventory
  reservation are not load-tested; under high concurrency use atomic conditional
  updates (or transactions on a replica set) when reserving stock.

## Key API groups

```
/api/v1/auth/customer/*        (register, login, 2fa verify/setup/confirm/disable)
/api/v1/auth/admin/*           (login, 2fa verify/setup/confirm)
/api/v1/admins/*
/api/v1/products , /api/v1/categories
/api/v1/orders/*
/api/v1/payments/*             (initiate + provider webhook stubs)
/api/v1/analytics/*
/api/v1/ml/*
/api/v1/settings/*             (store meta, public settings, admin settings)
/api/v1/admin/settings/upload-image  (hero / poster-card photos)
```

## ML capabilities included

- 7 / 30 / 90 day demand forecast per product (moving-average + trend; XGBoost-ready)
- Smart purchase recommendations (stock vs predicted demand)
- Product Intelligence Score (0–100) with labels
- Business Intelligence Center endpoints (top profit products, low-stock alerts, auto insights)

## Extending

1. Add real Stripe/PayPal/bKash/Nagad credentials in `.env` and complete the provider classes in `app/api/v1/payments.py`.
2. Replace the simple forecast with XGBoost/LightGBM training jobs under `ml/training/` and Celery workers.
3. Expand the Next.js admin pages (orders table, product form, inventory transfers, invoice PDF).
4. Wire React Query + Zustand for cart and auth state.

## Project layout

```
pal vsai/
  backend/          # FastAPI
  frontend/         # Next.js
  ml/               # datasets, training, models
  scripts/          # seed.py, test_2fa_flows.py
  infrastructure/   # docker, nginx
  docs/
  docker-compose.yml
```

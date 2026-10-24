# AGENTS.md

Guide for contributors and coding agents working in this repository. Read this before changing architecture, authentication, payments, or deployment configuration.

## Project summary

GlobalShop is a production-oriented monorepo for a single store that can operate in any country. It combines a Next.js storefront and ERP admin with a FastAPI API, MongoDB persistence, and demand-forecasting/BI endpoints.

- `backend/` — FastAPI 0.115, Pydantic v2, Motor (async MongoDB), JWT auth, TOTP 2FA, RBAC, invoices, ML endpoints.
- `frontend/` — Next.js App Router, React, TypeScript, Tailwind CSS, Recharts.
- `ml/` — space for datasets, training jobs, and model artifacts.
- `scripts/` — demo seed, load tests, security smoke test, 2FA regression tests, production env/deploy/backup helpers.
- `infrastructure/` — Caddy and MongoDB replica-set bootstrap for the production stack.
- `database/` — SQL-readable reference of the MongoDB model and demo catalog. Not executed by the app.
- `DEPLOYMENT.md` — VPS + Docker production runbook.
- `FREE_HOSTING.md` — Vercel + Render + Atlas free-tier runbook.
- `HowToSetup.md` — local and production setup guide.

## First-time setup

Follow [HowToSetup.md](HowToSetup.md). The short version:

```bash
# MongoDB
docker run -d --name globalshop-mongo -p 27017:27017 mongo:7

# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python ../scripts/seed.py
python -m uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Demo credentials are for local use only. Never seed a production or remote database.

## Commands

Backend, from `backend/`:

```bash
python -m uvicorn app.main:app --reload --port 8000
python -m compileall app
python ../scripts/test_2fa_flows.py
python ../scripts/security_smoke.py
python -m app.cli.admin list
python -m app.cli.admin create --email owner@example.com --name "Store Owner" --enroll-2fa
python -m app.cli.admin reset-password --email owner@example.com
python -m app.cli.bootstrap
```

On Windows use `.venv/Scripts/python.exe` instead of `python` when the environment is not activated.

Frontend, from `frontend/`:

```bash
npm run dev
npx tsc --noEmit
npm run lint
npm run build
```

Docker, from the repository root:

```bash
docker compose up --build
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

## Architecture facts that must stay true

### Data store

- MongoDB is the only runtime datastore. There is no SQL database, ORM, or migration framework.
- Collections: `admins`, `customers`, `categories`, `products`, `inventory`, `orders`, `payments`, `suppliers`, `site_settings`, `refresh_tokens`, `audit_logs`.
- Indexes are created at startup in `backend/app/core/database.py`. Add an index there when adding a new query pattern.
- `database/schema.sql` is a normalized reference for SQL tooling and review. Do not wire it into the runtime or treat it as a migration.
- Storefront settings are a single document in `site_settings` with `_id = "core"`. Defaults and deep-merge behavior live in `backend/app/api/v1/settings.py`.

### Authentication and authorization

- Customer and admin JWTs are separate: the `type` claim is enforced by dependencies in `backend/app/api/deps.py`. Customer tokens must never work on admin routes.
- Refresh tokens are stored in `refresh_tokens` with a unique `token_jti` and TTL. They cannot be used as access tokens.
- Admin login can return a short-lived 2FA challenge (`pending_2fa.jti` on the account). The challenge is bound to the account, single-use, expiring, and attempt-limited.
- Backup codes are bcrypt-hashed and single-use.
- Permissions are `module.action` strings; role defaults live in `backend/app/core/constants.py`. Main Admin is protected from disabling or privilege escalation by lower roles.
- Production admins must enroll 2FA. Do not weaken production validation or token checks.

### Checkout, inventory, and invoices

- Checkout reserves stock atomically with `find_one_and_update` and rolls reservations back if order creation fails.
- Delivered orders commit stock; cancelled orders release reservations. `stock_committed` and `stock_released` flags make the transitions idempotent.
- Invoice PDFs are generated into `UPLOAD_ROOT/invoices` and served through authenticated API responses.
- Order numbers are `ORDER_NUMBER_PREFIX + YYYYMMDD + 8 random digits`; the collection has a unique index.

### Payments

- Cash on Delivery is the only enabled method. `SUPPORTED_PAYMENT_METHODS` in `settings.py` intentionally excludes online gateways until they are integrated and tested.
- Payment callbacks must verify an HMAC signature or a valid Stripe signature, and must match the order's provider, amount, and method. Paid orders cannot be downgraded.
- Do not enable a gateway in settings merely by adding it to the UI; the backend allow-list and callback verification are the source of truth.

### Media and hosting

- Backend-served uploads use paths such as `/uploads/products/<file>`. On split deployments (Vercel + Render), frontend code must resolve them with `mediaUrl()` from `frontend/lib/api.ts`.
- `NEXT_PUBLIC_API_URL` is compiled at build time. Use `/api/v1` for same-origin Caddy deployments and an absolute API origin for split hosting.
- Next.js security headers and CSP are defined in `frontend/next.config.js`. Keep `connect-src` aligned with the API origin.
- Render free services have ephemeral disks and sleep after inactivity; Atlas M0 has small limits; Vercel Hobby is non-commercial. Do not design production features around free-tier persistence.

## Coding conventions

- Backend: async/await throughout; Motor for database access; Pydantic v2 models for request/response boundaries; `HTTPException(status_code, detail)` for API errors.
- Use timezone-aware UTC datetimes (`datetime.now(timezone.utc)`). BSON datetimes are read with `tz_aware=True`.
- Keep public API shapes backward compatible unless the task explicitly allows a breaking change.
- Frontend: TypeScript, App Router, functional components, Tailwind utilities, `lucide-react` icons, `react-hot-toast` for user feedback.
- Add comments only for non-obvious invariants, security decisions, or workarounds. Do not narrate code.
- Reuse the shared API client (`frontend/lib/api.ts`) instead of adding ad-hoc axios calls.
- Do not add dependencies, abstractions, or configuration for hypothetical future requirements.

## Testing expectations

- 2FA/auth changes: run `python ../scripts/test_2fa_flows.py` from `backend/`. All 28 checks must pass.
- API/runtime changes: at minimum run `python -m compileall app` and the relevant live smoke test with MongoDB running.
- Frontend changes: run `npx tsc --noEmit`, `npm run lint`, and `npm run build`.
- UI changes: exercise the golden path and edge cases in a browser, including mobile width where relevant.
- When changing the document model, update the SQL reference and `CHANGELOG.md`.

## Safety rules

- Never run `scripts/seed.py` against production, Atlas, or any shared database. It deletes collections and is guarded only as a safety net.
- Never commit `.env`, `.env.production`, `.env.local`, credentials, private keys, backups, or generated invoices.
- Do not weaken or bypass production config validation, rate limits, CORS restrictions, proxy-header trust, payment signature checks, or admin/customer token separation.
- Do not enable online payment methods without a real provider integration and verified signed callbacks.
- Treat changes to Atlas allowlists, deployed services, DNS, and production infrastructure as actions that require explicit user approval.
- Validate uploads by content, not filename or client MIME type.
- Keep the preview gate, admin credentials, and tunnel URLs out of the repository.

## Change checklist

1. Make the smallest change that solves the task.
2. Run the relevant tests and builds listed above.
3. Update `CHANGELOG.md` for user-visible or operational changes.
4. Update `README.md`, `HowToSetup.md`, `DEPLOYMENT.md`, or `FREE_HOSTING.md` when behavior or setup changes.
5. If the Mongo document model changes, update `database/schema.sql` and `database/seed.sql` as reference artifacts.

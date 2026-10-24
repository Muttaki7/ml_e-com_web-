# Changelog

All notable changes to GlobalShop are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses semantic versioning.

## [1.0.0] - 2026-10-25

First production-oriented release of the global commerce, ERP, and machine-learning platform.

### Added

- Global store configuration: 223 countries, currency and timezone sync, domestic/international delivery pricing, E.164 phone validation, and ISO-3166 addresses.
- Separate customer and admin authentication with JWT type enforcement, RBAC permissions, refresh-token rotation, and audit logging.
- TOTP two-factor authentication for admins and customers, including QR enrollment, bcrypt-hashed single-use backup codes, account-bound single-use challenges, and per-account attempt lockouts.
- Admin-managed hero banner and poster-card slideshows with validated JPEG/PNG/WebP/GIF uploads and configurable visibility.
- Storefront, cart, checkout, customer order history, PDF invoices, and the ERP dashboard for orders, products, categories, inventory, administrators, settings, analytics, and ML.
- Demand forecasting (7/30/90 days), smart purchase recommendations, Product Intelligence Score, and the Business Intelligence Center.
- Cash on Delivery checkout with atomic stock reservation, idempotent commit/release flags, and authenticated online-payment callback scaffolding that stays disabled until configured.
- Production Docker stack with Caddy automatic HTTPS, MongoDB 7 authentication and replica set, Redis shared rate limits, health checks, backups, and GitHub Actions CI.
- Free staging path: Render Blueprint, Vercel configuration, MongoDB Atlas support, split-origin media resolution, and idempotent hosted admin/demo bootstrap.
- Repository documentation: `HowToSetup.md`, `AGENTS.md`, this changelog, and a SQL-readable database reference (`database/schema.sql`, `database/seed.sql`).

### Changed

- The frontend now defaults to a same-origin API (`/api/v1`) for bundled Docker/Caddy deployments; split hosting uses an absolute `NEXT_PUBLIC_API_URL`.
- Vercel builds skip the standalone Next.js output, while self-hosted and Docker builds keep it.
- CORS automatically includes `FRONTEND_URL`, and allowed hosts automatically include Render's runtime hostname.
- Uploaded media is resolved through `mediaUrl()` so backend-hosted images work when the storefront and API run on different origins.
- Production configuration refuses unsafe defaults at startup, including debug mode, short secrets, missing Redis, HTTP frontend URLs, empty allowed hosts, and wildcard/localhost CORS.
- Checkout reserves stock atomically and releases it on failure; delivery commits stock and cancellation returns it.
- Invoice generation is refreshed after order status changes.

### Fixed

- Refresh tokens can no longer be used as access tokens; refresh rotation and logout revocation are enforced.
- Payment callbacks require a valid signature, matching provider, matching amount, and cannot downgrade a paid order.
- Login timing is equalized for unknown accounts, and password/2FA brute force attempts are rate-limited and locked out.
- Client IP resolution ignores forwarded headers unless explicitly behind a trusted proxy.
- Product image uploads validate magic bytes and derive the stored extension from the detected type.
- Order, inventory, and ML calculations handle sparse data and concurrent updates safely.
- Admin 2FA enrollment and challenge handling reject replayed, unbound, and expired temp tokens.

### Security

- Production secrets, database credentials, and deployment environment files are excluded from version control.
- The demo seed refuses production and remote databases unless an explicit disposable-environment override is set.
- Audit logs record authentication, admin, order, and settings events.
- Documentation calls out the demo credentials and requires rotation plus 2FA before public exposure.

### Known limitations

- Online payment gateways (card, PayPal, bKash, Nagad, Rocket) are code-ready but disabled until real merchant credentials and signed callbacks are verified.
- Email delivery depends on external SMTP configuration; local development uses logging/no-op delivery.
- Free-tier deployments have sleeping services, ephemeral upload storage, and limited database capacity; use the VPS stack for production persistence.

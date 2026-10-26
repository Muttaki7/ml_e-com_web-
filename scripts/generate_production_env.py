#!/usr/bin/env python3
"""Generate .env.production and fresh secrets for the Docker production stack.

Usage:
  python scripts/generate_production_env.py --host shop.example.com --email ops@example.com
  python scripts/generate_production_env.py --host 203.0.113.10   # -> 203.0.113.10.sslip.io

The generated file is git-ignored and must be backed up securely: it holds the
database, Redis and JWT secrets for the deployment.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.production"
DEFAULT_EMAIL = "admin@example.com"
DOMAIN_RE = re.compile(
    r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def random_alnum(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalise_host(raw: str) -> tuple[str, str | None]:
    value = raw.strip().lower()
    value = re.sub(r"^[a-z]+://", "", value, flags=re.I)
    value = value.split("/")[0].split("?")[0]
    if value.count(":") == 1:
        value = value.split(":")[0]  # drop a port, if supplied
    if not value:
        raise SystemExit("ERROR: --host is empty.")
    if value in {"localhost", "127.0.0.1", "0.0.0.0"} or value.endswith(".local"):
        raise SystemExit("ERROR: --host must be a public hostname or public IPv4 address.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        if not DOMAIN_RE.fullmatch(value):
            raise SystemExit(
                "ERROR: --host must be a valid domain (shop.example.com) or IPv4 address. "
                "Use punycode for international domains."
            )
        return value, None
    if address.version != 4:
        raise SystemExit("ERROR: IPv6 is not supported for the automatic sslip.io hostname.")
    host = f"{value}.sslip.io"
    note = f"{value} is an IP, so the public hostname is {host} (sslip.io resolves it automatically)."
    return host, note


def write_env(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Public domain or IPv4 address")
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"ACME contact email for TLS certificates (default: {DEFAULT_EMAIL})",
    )
    parser.add_argument("--country", default="US", help="Default store country (ISO 3166-1 alpha-2)")
    parser.add_argument("--db", default="global_ecommerce_erp", help="MongoDB database name")
    parser.add_argument("--workers", type=int, default=2, help="Uvicorn worker processes (default: 2)")
    parser.add_argument(
        "--mongo-cache-gb",
        type=float,
        default=0.5,
        help="MongoDB WiredTiger cache size in GB (default: 0.5)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an existing .env.production")
    args = parser.parse_args()

    if ENV_FILE.exists() and not args.force:
        raise SystemExit(
            f"ERROR: {ENV_FILE} already exists. Re-run with --force to replace it "
            "(all current secrets will be invalidated)."
        )
    if not os.environ.get("CI") and ENV_FILE.exists() and args.force:
        print("Replacing the existing .env.production and rotating all secrets.", file=sys.stderr)
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", args.db):
        raise SystemExit("ERROR: --db must be alphanumeric/underscore.")
    country = args.country.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise SystemExit("ERROR: --country must be an ISO 3166-1 alpha-2 code, e.g. US or BD.")
    if not 1 <= args.workers <= 16:
        raise SystemExit("ERROR: --workers must be between 1 and 16.")
    if args.mongo_cache_gb < 0.25:
        raise SystemExit("ERROR: --mongo-cache-gb must be at least 0.25.")

    host, note = normalise_host(args.host)
    if note is None and not host.startswith("www."):
        site_hosts = [host, f"www.{host}"]
    else:
        site_hosts = [host]
    site_address = ",".join(site_hosts)
    allowed_hosts = ",".join(site_hosts)
    cors_origins = ",".join(f"https://{h}" for h in site_hosts)
    email = args.email.strip() or DEFAULT_EMAIL
    if "@" not in email or email.endswith("@"):
        raise SystemExit("ERROR: --email does not look like a valid email address.")
    if email == DEFAULT_EMAIL:
        print(
            f"WARNING: using {DEFAULT_EMAIL} for TLS notices; pass --email to receive expiry alerts.",
            file=sys.stderr,
        )

    secret_key = secrets.token_urlsafe(64)
    callback_secret = secrets.token_urlsafe(48)
    mongo_root_user = "root"
    mongo_root_password = random_alnum(40)
    mongo_app_user = "app"
    mongo_app_password = random_alnum(40)
    redis_password = random_alnum(40)

    mongo_uri = (
        f"mongodb://{mongo_app_user}:{mongo_app_password}@mongodb:27017/{args.db}"
        "?replicaSet=rs0&authSource=admin"
    )
    redis_uri = f"redis://:{redis_password}@redis:6379/0"
    public_url = f"https://{host}"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = f"""# Production environment for docker-compose.prod.yml
# Generated {generated_at} by scripts/generate_production_env.py
# KEEP PRIVATE. Back this file up; losing it makes existing secrets unrecoverable.
# Every command must run with: docker compose --env-file .env.production -f docker-compose.prod.yml

COMPOSE_PROJECT_NAME=global-erp
IMAGE_TAG=latest

# --- Application -----------------------------------------------------------
APP_ENV=production
DEBUG=false
SECRET_KEY={secret_key}
WEB_CONCURRENCY={args.workers}
MAX_REQUEST_BODY_BYTES=12582912
FRONTEND_URL={public_url}
CORS_ORIGINS={cors_origins}
ALLOWED_HOSTS={allowed_hosts}
TRUST_PROXY_HEADERS=true
STORE_COUNTRY={country}
TZ=UTC

# --- Edge / TLS ------------------------------------------------------------
SITE_ADDRESS={site_address}
ACME_EMAIL={email}
NEXT_PUBLIC_API_URL=/api/v1

# --- MongoDB ---------------------------------------------------------------
MONGODB_DB={args.db}
MONGODB_URI={mongo_uri}
MONGODB_MAX_POOL_SIZE=50
MONGO_ROOT_USERNAME={mongo_root_user}
MONGO_ROOT_PASSWORD={mongo_root_password}
MONGO_APP_USERNAME={mongo_app_user}
MONGO_APP_PASSWORD={mongo_app_password}
MONGO_WIREDTIGER_CACHE_GB={args.mongo_cache_gb}

# --- Redis (shared rate limiting / sessions) -------------------------------
REDIS_PASSWORD={redis_password}
REDIS_URL={redis_uri}
RATE_LIMIT_STORAGE_URI={redis_uri}

# --- Payments --------------------------------------------------------------
# COD is the only method exposed at checkout. Online gateways stay disabled
# in Admin -> Settings until real credentials are configured and verified.
PAYMENT_CALLBACK_SECRET={callback_secret}
# STRIPE_SECRET_KEY=
# STRIPE_WEBHOOK_SECRET=
# PAYPAL_CLIENT_ID=
# PAYPAL_CLIENT_SECRET=
# BKASH_API_KEY=
# BKASH_SECRET=
# BKASH_USERNAME=
# BKASH_PASSWORD=
# NAGAD_MERCHANT_ID=
# NAGAD_API_KEY=
# ROCKET_MERCHANT_ID=
# ROCKET_API_KEY=

# --- Transactional email (optional) ---------------------------------------
# When SMTP_HOST is empty, order emails are skipped and checkout still works.
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=
# SMTP_PASSWORD=
# SMTP_FROM=Shop <no-reply@example.com>
# SMTP_STARTTLS=true
# SMTP_SSL=false
# SUPPORT_EMAIL=support@example.com
"""
    write_env(ENV_FILE, content)

    print(f"Wrote {ENV_FILE}")
    if note:
        print(note)
    print(f"Public URL: {public_url}")
    print()
    print("Next steps:")
    if note:
        print("  1. DNS: no setup needed for the sslip.io hostname.")
    else:
        print(f"  1. DNS: point A records for {', '.join(site_hosts)} at this server's public IPv4.")
    print("  2. Firewall: allow TCP 22, 80, 443 and UDP 443; never expose 27017 or 6379.")
    print("  3. Start the stack: ./scripts/deploy.sh")
    print("  4. Create the owner account and enroll 2FA:")
    print(
        "       docker compose --env-file .env.production -f docker-compose.prod.yml "
        "exec backend python -m app.cli.admin create --email you@example.com "
        '--name "Store Owner" --enroll-2fa'
    )
    print("  5. Store the .env.production file in a password manager / encrypted backup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

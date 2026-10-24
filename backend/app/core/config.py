import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-to-a-long-random-string-at-least-64-chars"
PRODUCTION_ENVS = {"production", "prod", "live"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Global Commerce ERP"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "UTC"
    CURRENCY: str = "USD"
    CURRENCY_SYMBOL: str = "$"
    # Used to distinguish domestic vs international delivery when the admin
    # has not set a store country in site settings.
    STORE_COUNTRY: str = "US"
    ORDER_NUMBER_PREFIX: str = "ORD"

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "global_ecommerce_erp"
    MONGODB_MAX_POOL_SIZE: int = 100

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    ADMIN_REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    TOTP_ISSUER: str = "Global-ERP"
    TOTP_DIGITS: int = 6
    TOTP_INTERVAL: int = 30
    MAX_2FA_ATTEMPTS: int = 5
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15

    RATE_LIMIT_PER_MINUTE: int = 60
    # Shared storage (Redis) is required in production so every worker enforces
    # the same counters. Empty means per-process memory (development only).
    RATE_LIMIT_STORAGE_URI: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    # Only enable when every request passes through a proxy you control that
    # overwrites X-Forwarded-For. Otherwise clients can spoof their IP.
    TRUST_PROXY_HEADERS: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    ALLOWED_HOSTS: str = ""
    MAX_REQUEST_BODY_BYTES: int = 12 * 1024 * 1024

    # International card payments (Stripe)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_BASE_URL: str = "https://api.stripe.com/v1"
    # Shared HMAC-SHA256 secret for gateway callbacks (X-Payment-Signature).
    # When empty, payment callbacks are rejected until configured.
    PAYMENT_CALLBACK_SECRET: str = ""

    # PayPal
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"

    # Bangladesh mobile-banking providers (enable only for BD deployments)
    BKASH_API_KEY: str = ""
    BKASH_SECRET: str = ""
    BKASH_USERNAME: str = ""
    BKASH_PASSWORD: str = ""
    BKASH_BASE_URL: str = "https://tokenized.sandbox.bka.sh/v1.2.0-beta"

    NAGAD_MERCHANT_ID: str = ""
    NAGAD_API_KEY: str = ""
    NAGAD_BASE_URL: str = ""

    ROCKET_MERCHANT_ID: str = ""
    ROCKET_API_KEY: str = ""

    FRONTEND_URL: str = "http://localhost:3000"

    # Writable directory for uploaded images and generated invoices. Empty means
    # the repository-level uploads/ folder (local development).
    UPLOAD_ROOT: str = ""

    # Transactional email (optional). When SMTP_HOST is empty, emails are skipped.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    SMTP_SSL: bool = False
    SUPPORT_EMAIL: str = ""

    # One-time hosted bootstrap (Render/Fly/etc. without shell access).
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
    BOOTSTRAP_ADMIN_NAME: str = "Store Owner"
    BOOTSTRAP_DEMO_DATA: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() in PRODUCTION_ENVS

    @property
    def docs_enabled(self) -> bool:
        return self.DEBUG and not self.is_production

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]
        frontend = self.FRONTEND_URL.strip().rstrip("/")
        if frontend and frontend not in origins:
            origins.append(frontend)
        return origins

    @property
    def allowed_hosts_list(self) -> List[str]:
        hosts = [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]
        # Render assigns the public hostname at runtime; trust only the value it
        # injects, never a client-supplied header.
        render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
        if render_host and render_host not in hosts:
            hosts.append(render_host)
        return hosts

    def validate_runtime(self) -> None:
        """Refuse to boot a production deployment with unsafe defaults."""
        if not self.is_production:
            return

        problems: List[str] = []
        if self.DEBUG:
            problems.append("DEBUG must be false in production")
        if not self.SECRET_KEY or self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be a random value of at least 32 characters")
        if not self.TRUST_PROXY_HEADERS:
            problems.append("TRUST_PROXY_HEADERS must be true behind the bundled reverse proxy")
        if not self.RATE_LIMIT_STORAGE_URI.startswith(("redis://", "rediss://")):
            problems.append("RATE_LIMIT_STORAGE_URI must point at Redis in production")
        if not self.FRONTEND_URL.startswith("https://"):
            problems.append("FRONTEND_URL must be an https URL in production")
        if not self.allowed_hosts_list:
            problems.append("ALLOWED_HOSTS must list the public hostname in production")

        origins = self.cors_origins_list
        if not origins:
            problems.append("CORS_ORIGINS must contain the public storefront origin")
        for origin in origins:
            if origin == "*" or not origin.startswith("https://"):
                problems.append("CORS_ORIGINS entries must be explicit https origins")
                break
            if "localhost" in origin or "127.0.0.1" in origin:
                problems.append("CORS_ORIGINS cannot contain localhost in production")
                break

        online_configured = any(
            [
                self.STRIPE_SECRET_KEY,
                self.PAYPAL_CLIENT_ID,
                self.BKASH_API_KEY,
                self.NAGAD_MERCHANT_ID,
                self.ROCKET_MERCHANT_ID,
            ]
        )
        if online_configured and not self.PAYMENT_CALLBACK_SECRET:
            problems.append("PAYMENT_CALLBACK_SECRET is required when an online gateway is configured")

        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

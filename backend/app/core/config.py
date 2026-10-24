from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-to-a-long-random-string-at-least-64-chars"


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
    # Only enable when every request passes through a proxy you control that
    # overwrites X-Forwarded-For. Otherwise clients can spoof their IP.
    TRUST_PROXY_HEADERS: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

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

    REDIS_URL: str = "redis://localhost:6379/0"
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

from slowapi import Limiter

from app.core.client_ip import client_ip
from app.core.config import settings


# Redis keeps counters shared across Uvicorn workers. Development without Redis
# falls back to per-process memory, which is fine for a single local process.
limiter = Limiter(
    key_func=client_ip,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI or None,
    swallow_errors=not settings.is_production,
)

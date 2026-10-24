from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def client_key(request) -> str:
    """Rate-limit key that only honors X-Forwarded-For behind a trusted proxy."""
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_key)

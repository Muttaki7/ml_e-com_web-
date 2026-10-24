from fastapi import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Client IP, honoring proxy headers only when the proxy is trusted.

    Caddy overwrites both X-Real-IP and X-Forwarded-For at the edge. The last
    X-Forwarded-For entry is used as a fallback because a proxy that appends
    puts the immediate peer there, while earlier entries can be client-supplied.
    """
    if settings.TRUST_PROXY_HEADERS:
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"

from typing import Optional

from redis.asyncio import Redis

from app.core.config import settings

redis_client: Optional[Redis] = None


async def connect_redis() -> None:
    global redis_client
    if not settings.RATE_LIMIT_STORAGE_URI:
        return
    redis_client = Redis.from_url(settings.RATE_LIMIT_STORAGE_URI, decode_responses=True)
    await redis_client.ping()


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def redis_healthy() -> bool:
    if redis_client is None:
        return True
    try:
        return bool(await redis_client.ping())
    except Exception:
        return False

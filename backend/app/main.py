from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings
from app.core.database import connect_db, close_db, database_healthy
from app.core.limiter import limiter
from app.core.paths import UPLOAD_ROOT
from app.core.redis import close_redis, connect_redis, redis_healthy
from app.api.v1 import auth, admins, products, orders, payments, analytics, ml
from app.api.v1 import settings as settings_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_runtime()
    await connect_db()
    await connect_redis()
    logger.info(
        "service.ready",
        db=settings.MONGODB_DB,
        environment=settings.APP_ENV,
        production=settings.is_production,
    )
    yield
    await close_redis()
    await close_db()
    logger.info("service.stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="Global E-Commerce + ERP + Machine Learning Platform",
    version="1.0.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

if settings.allowed_hosts_list:
    # Health probes use localhost; public traffic arrives with the real host.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts_list + ["localhost", "127.0.0.1"],
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


# Mount routers under /api/v1
prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(admins.router, prefix=prefix)
app.include_router(products.router, prefix=prefix)
app.include_router(orders.router, prefix=prefix)
app.include_router(payments.router, prefix=prefix)
app.include_router(analytics.router, prefix=prefix)
app.include_router(ml.router, prefix=prefix)
app.include_router(settings_router.router, prefix=prefix)


# Serve uploaded product images
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")


@app.get("/")
async def root():
    payload = {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "currency": settings.CURRENCY,
        "timezone": settings.TIMEZONE,
    }
    if settings.docs_enabled:
        payload["docs"] = "/docs"
    return payload


@app.get("/health")
async def health():
    """Liveness: the process is up."""
    return {"status": "ok"}


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready(response: Response):
    """Readiness: dependencies required to serve traffic are reachable."""
    checks = {
        "mongodb": await database_healthy(),
        "redis": await redis_healthy(),
    }
    healthy = all(checks.values())
    response.status_code = 200 if healthy else 503
    return {"status": "ok" if healthy else "unavailable", "checks": checks}


# Baseline security headers, request-size guard and access logging
@app.middleware("http")
async def request_guard(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return ORJSONResponse({"detail": "Request body too large"}, status_code=413)
        except ValueError:
            return ORJSONResponse({"detail": "Invalid Content-Length header"}, status_code=400)

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if request.url.scheme == "https" or settings.is_production:
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    if settings.DEBUG or response.status_code >= 400:
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        )
    return response

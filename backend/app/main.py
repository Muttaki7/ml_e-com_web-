from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

from app.core.config import settings, DEFAULT_SECRET_KEY
from app.core.database import connect_db, close_db
from app.core.limiter import limiter
from app.api.v1 import auth, admins, products, orders, payments, analytics, ml
from app.api.v1 import settings as settings_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.DEBUG and (
        settings.SECRET_KEY == DEFAULT_SECRET_KEY or len(settings.SECRET_KEY) < 32
    ):
        raise RuntimeError(
            "SECRET_KEY must be set to a long random value before running in production"
        )
    await connect_db()
    logger.info("mongodb.connected", db=settings.MONGODB_DB)
    yield
    await close_db()
    logger.info("mongodb.closed")


app = FastAPI(
    title=settings.APP_NAME,
    description="Global E-Commerce + ERP + Machine Learning Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "currency": settings.CURRENCY,
        "timezone": settings.TIMEZONE,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# Simple request logging middleware + baseline security headers
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
    )
    if request.url.scheme == "https":
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
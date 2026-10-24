import aiofiles
from copy import deepcopy
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.core.database import get_db
from app.core.config import settings
from app.core.countries import COUNTRIES, get_country
from app.core.paths import UPLOAD_ROOT
from app.api.deps import require_permission

router = APIRouter(tags=["Settings"])

CORE_ID = "core"
MAX_SLIDESHOW_IMAGES = 12
MAX_IMAGE_URL_LENGTH = 1000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
UPLOAD_DIR = UPLOAD_ROOT / "site"
# Online gateways remain code-complete but are intentionally not offered until
# real provider credentials and webhook testing are in place. COD is always
# safe to expose because no external provider is involved.
SUPPORTED_PAYMENT_METHODS = {"cod"}

DEFAULT_SETTINGS: dict = {
    "store": {
        "country": settings.STORE_COUNTRY,
        "currency": settings.CURRENCY,
        "currency_symbol": settings.CURRENCY_SYMBOL,
        "timezone": settings.TIMEZONE,
    },
    "banner": {
        "badge": "AI-powered pricing & stock forecasting",
        "title": "Shop smarter, anywhere in the world",
        "subtitle": (
            "Products from trusted sellers. Cash on Delivery — "
            "delivered to 200+ countries and territories."
        ),
        "images": [],
    },
    "posters": [
        {"title": "Big Sale", "subtitle": "Up to 50% off electronics", "accent": "from-rose-500 to-orange-400", "visible": True, "images": []},
        {"title": "Best Price", "subtitle": "Everyday low prices", "accent": "from-emerald-500 to-teal-400", "visible": True, "images": []},
        {"title": "Free Delivery", "subtitle": "On orders above the set threshold", "accent": "from-sky-500 to-cyan-400", "visible": True, "images": []},
        {"title": "New Arrivals", "subtitle": "Fresh collection every week", "accent": "from-indigo-500 to-violet-400", "visible": True, "images": []},
    ],
    "delivery": {
        "local_charge": 5.0,
        "international_charge": 25.0,
        "free_delivery_enabled": True,
        "free_delivery_threshold": 50.0,
    },
    "payments": {
        "methods": [
            {"id": "cod", "label": "Cash on Delivery", "enabled": True},
            {"id": "card", "label": "Credit / Debit Card", "enabled": False},
            {"id": "paypal", "label": "PayPal", "enabled": False},
            {"id": "bkash", "label": "bKash (Bangladesh)", "enabled": False},
            {"id": "nagad", "label": "Nagad (Bangladesh)", "enabled": False},
            {"id": "rocket", "label": "Rocket (Bangladesh)", "enabled": False},
        ],
    },
    "company": {
        "name": "Global Commerce + ERP",
        "address": "",
        "support_email": "support@example.com",
        "support_phone": "",
    },
}


def _deep_merge(base: dict, updates: dict) -> dict:
    out = dict(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _safe_image_url(raw: object) -> Optional[str]:
    """Accept only http(s) links or root-relative paths for image sources."""
    if not isinstance(raw, str):
        return None
    url = raw.strip()
    if not url or len(url) > MAX_IMAGE_URL_LENGTH:
        return None
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        return None
    parsed = urlparse(url)
    if parsed.scheme:
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return None
    elif url.startswith("//") or not url.startswith("/"):
        return None
    return url


def _normalize_images(images: List[str]) -> List[str]:
    cleaned: List[str] = []
    for raw in images:
        if isinstance(raw, str) and not raw.strip():
            continue
        url = _safe_image_url(raw)
        if not url:
            raise ValueError("Each image must be an http(s) URL or a root-relative path")
        if url not in cleaned:
            cleaned.append(url)
    if len(cleaned) > MAX_SLIDESHOW_IMAGES:
        raise ValueError(f"At most {MAX_SLIDESHOW_IMAGES} images are allowed")
    return cleaned


def _safe_images(images: object) -> List[str]:
    if not isinstance(images, list):
        return []
    out: List[str] = []
    for raw in images:
        url = _safe_image_url(raw)
        if url and url not in out:
            out.append(url)
        if len(out) >= MAX_SLIDESHOW_IMAGES:
            break
    return out


def _apply_defaults(doc: dict) -> dict:
    """Fill missing keys from defaults so the API always returns a complete object."""
    merged = deepcopy(_deep_merge(DEFAULT_SETTINGS, doc or {}))

    banner = merged.get("banner")
    if not isinstance(banner, dict):
        banner = deepcopy(DEFAULT_SETTINGS["banner"])
    banner["images"] = _safe_images(banner.get("images"))
    merged["banner"] = banner

    # Poster cards always have a fixed length for the storefront grid.
    raw_posters = merged.get("posters")
    if not isinstance(raw_posters, list):
        raw_posters = []
    posters = []
    for raw in raw_posters[:4]:
        if not isinstance(raw, dict):
            continue
        poster = {
            "title": "",
            "subtitle": "",
            "accent": "from-sky-500 to-indigo-600",
            "visible": True,
            "images": [],
            **raw,
        }
        poster["images"] = _safe_images(poster.get("images"))
        poster["visible"] = bool(poster.get("visible", True))
        posters.append(poster)
    for default in DEFAULT_SETTINGS["posters"][len(posters):]:
        posters.append(deepcopy(default))
    merged["posters"] = posters

    payments = merged.get("payments")
    if not isinstance(payments, dict):
        payments = {}
    methods = payments.get("methods")
    if not isinstance(methods, list) or not methods:
        methods = deepcopy(DEFAULT_SETTINGS["payments"]["methods"])
    cleaned_methods = []
    for raw in methods:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        method = dict(raw)
        method["enabled"] = bool(method.get("enabled")) and method["id"] in SUPPORTED_PAYMENT_METHODS
        if method["id"] == "cod":
            # COD is the guaranteed launch method; online gateways are opt-in
            # only after provider credentials and webhook tests exist.
            method["enabled"] = True
        cleaned_methods.append(method)
    payments["methods"] = cleaned_methods
    merged["payments"] = payments
    return merged


async def get_settings_doc() -> dict:
    db = get_db()
    doc = await db.site_settings.find_one({"_id": CORE_ID})
    doc.pop("_id", None) if doc else None
    return _apply_defaults(doc)


async def get_store_meta() -> dict:
    """Resolve the effective store currency/country (site settings override env)."""
    s = await get_settings_doc()
    store = s.get("store") or {}
    return {
        "country": (store.get("country") or settings.STORE_COUNTRY).upper(),
        "currency": store.get("currency") or settings.CURRENCY,
        "currency_symbol": store.get("currency_symbol") or settings.CURRENCY_SYMBOL,
        "timezone": store.get("timezone") or settings.TIMEZONE,
    }


async def get_delivery_charge(subtotal: float, country: str) -> float:
    """Admin-configured delivery charge: local vs international, free above threshold."""
    s = await get_settings_doc()
    delivery = s.get("delivery") or {}
    threshold = float(delivery.get("free_delivery_threshold", 0) or 0)
    enabled = bool(delivery.get("free_delivery_enabled", False))
    if enabled and threshold > 0 and subtotal >= threshold:
        return 0.0
    meta = await get_store_meta()
    is_local = (country or "").strip().upper() == meta["country"]
    if is_local:
        return float(delivery.get("local_charge", 0) or 0)
    return float(delivery.get("international_charge", 0) or 0)


def enabled_payment_methods(doc: dict) -> list[dict]:
    methods = ((doc or {}).get("payments") or {}).get("methods") or []
    return [
        m for m in methods
        if m.get("enabled") and m.get("id") in SUPPORTED_PAYMENT_METHODS
    ]


class StoreIn(BaseModel):
    country: Optional[str] = None
    currency: Optional[str] = None
    currency_symbol: Optional[str] = None
    timezone: Optional[str] = None


class BannerIn(BaseModel):
    badge: str = ""
    title: str = ""
    subtitle: str = ""
    images: Optional[List[str]] = None

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        return None if value is None else _normalize_images(value)


class PosterIn(BaseModel):
    title: str = ""
    subtitle: str = ""
    accent: str = "from-sky-500 to-indigo-600"
    visible: bool = True
    images: Optional[List[str]] = None

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        return None if value is None else _normalize_images(value)


class DeliveryIn(BaseModel):
    local_charge: float = Field(0, ge=0)
    international_charge: float = Field(0, ge=0)
    free_delivery_enabled: bool = False
    free_delivery_threshold: float = Field(0, ge=0)


class PaymentMethodIn(BaseModel):
    id: str
    label: str = ""
    enabled: bool = True


class PaymentsIn(BaseModel):
    methods: List[PaymentMethodIn] = []


class CompanyIn(BaseModel):
    name: str = ""
    address: str = ""
    support_email: str = ""
    support_phone: str = ""


class SettingsUpdate(BaseModel):
    store: Optional[StoreIn] = None
    banner: Optional[BannerIn] = None
    posters: Optional[List[PosterIn]] = Field(default=None, max_length=4)
    delivery: Optional[DeliveryIn] = None
    payments: Optional[PaymentsIn] = None
    company: Optional[CompanyIn] = None


@router.get("/meta/countries")
async def list_countries(response: Response):
    """ISO country reference (code, name, dial code, currency) for selectors."""
    response.headers["Cache-Control"] = "public, max-age=86400"
    return COUNTRIES


@router.get("/settings/public")
async def public_settings(response: Response):
    """Public storefront settings (store, banner, posters, delivery, payments)."""
    response.headers["Cache-Control"] = "public, max-age=5, stale-while-revalidate=25"
    doc = await get_settings_doc()
    meta = await get_store_meta()
    doc["store"] = meta
    return doc


@router.get("/admin/settings")
async def admin_get_settings(
    admin: dict = Depends(require_permission("settings.view")),
):
    return await get_settings_doc()


@router.put("/admin/settings")
async def admin_update_settings(
    body: SettingsUpdate,
    admin: dict = Depends(require_permission("settings.edit")),
):
    db = get_db()
    current = await get_settings_doc()
    update = body.model_dump(exclude_none=True)
    if "payments" in update:
        for method in update["payments"].get("methods", []):
            if method.get("enabled") and method.get("id") not in SUPPORTED_PAYMENT_METHODS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{method.get('label') or method.get('id')} is not available yet. "
                        "Configure and test the provider before enabling it."
                    ),
                )
    if "store" in update and update["store"].get("country"):
        country = get_country(update["store"]["country"])
        if not country:
            raise HTTPException(status_code=400, detail="Unknown store country")
        update["store"]["country"] = country["code"]
    merged = _deep_merge(current, update)
    merged["updated_by"] = admin["id"]
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.site_settings.replace_one(
        {"_id": CORE_ID},
        {**merged, "_id": CORE_ID},
        upsert=True,
    )
    return _apply_defaults(merged)


def _detect_image(data: bytes) -> Optional[tuple[str, str]]:
    """Return (mime, extension) from magic bytes; never trust the filename."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", ".gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


@router.post("/admin/settings/upload-image")
async def upload_settings_image(
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(require_permission("settings.edit")),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Only JPEG, PNG, WEBP or GIF images are allowed")
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image exceeds the 5 MB limit")
    detected = _detect_image(data)
    if not detected:
        raise HTTPException(400, "File content is not a valid image")
    _, ext = detected
    name = f"{uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(UPLOAD_DIR / name, "wb") as fh:
        await fh.write(data)
    base = str(request.base_url).rstrip("/")
    return {"url": f"{base}/uploads/site/{name}", "filename": name}

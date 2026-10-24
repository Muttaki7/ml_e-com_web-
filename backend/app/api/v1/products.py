from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import re
import aiofiles
from fastapi import APIRouter, Depends, Query, HTTPException, Request, UploadFile, File
from bson import ObjectId


from app.core.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductOut, CategoryCreate, CategoryOut
from app.api.deps import get_current_admin, require_permission, get_current_customer
from app.core.constants import StockStatus

router = APIRouter(tags=["Products & Categories"])


def _to_oid(value: str, label: str = "id"):
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


def _slug(text: str) -> str:
    try:
        from slugify import slugify
        return slugify(text)
    except Exception:
        return text.lower().replace(" ", "-")[:80]


async def _resolve_category_id(db, raw: str) -> ObjectId:
    """Resolve a category reference into a real category ObjectId.

    The admin product form sends prebuilt categories by NAME (or a
    "Parent > Child" path) as well as existing DB ObjectIds. Anything not an
    existing ObjectId is looked up (case-insensitive) under its parent and
    created if missing, so prebuilt selections always persist a reusable
    category document for the storefront and future product forms.
    """
    raw = (raw or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Category is required")

    parts = [p.strip() for p in re.split(r"\s*>\s*", raw) if p.strip()]
    parent_id: Optional[ObjectId] = None

    for part in parts:
        # Existing DB category id (single-id selection or a path segment)
        if ObjectId.is_valid(part):
            cat = await db.categories.find_one({"_id": ObjectId(part)})
            if cat:
                if cat.get("status") == "deleted":
                    await db.categories.update_one(
                        {"_id": cat["_id"]},
                        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc)}},
                    )
                parent_id = cat["_id"]
                continue
        # Prebuilt / by-name category under the current parent
        cat = await db.categories.find_one({
            "name": {"$regex": f"^{re.escape(part)}$", "$options": "i"},
            "parent_id": parent_id,
            "status": {"$ne": "deleted"},
        })
        if not cat:
            cat = await db.categories.find_one({
                "slug": _slug(part),
                "parent_id": parent_id,
                "status": {"$ne": "deleted"},
            })
        if not cat:
            now = datetime.now(timezone.utc)
            res = await db.categories.insert_one({
                "name": part,
                "slug": await _unique_slug(db, _slug(part)),
                "parent_id": parent_id,
                "description": None,
                "image": None,
                "order": 0,
                "status": "active",
                "created_at": now,
                "updated_at": now,
            })
            cat = {"_id": res.inserted_id}
        parent_id = cat["_id"]

    if not parent_id:
        raise HTTPException(status_code=400, detail="Invalid category")
    return parent_id


def _serialize_product(p: dict) -> dict:
    final = p.get("selling_price", 0) * (1 - p.get("discount_percent", 0) / 100)
    stock = p.get("stock_quantity", 0)
    min_s = p.get("min_stock_level", 5)
    if stock <= 0:
        status = StockStatus.OUT_OF_STOCK
    elif stock <= min_s:
        status = StockStatus.LOW_STOCK
    else:
        status = StockStatus.IN_STOCK
    return {
        "id": str(p["_id"]),
        "name": p.get("name"),
        "slug": p.get("slug"),
        "sku": p.get("sku"),
        "barcode": p.get("barcode"),
        "description": p.get("description"),
        "specifications": p.get("specifications"),
        "category_id": str(p.get("category_id")) if p.get("category_id") else None,
        "brand": p.get("brand"),
        "purchase_price": p.get("purchase_price", 0),
        "selling_price": p.get("selling_price", 0),
        "discount_percent": p.get("discount_percent", 0),
        "tax_percent": p.get("tax_percent", 0),
        "final_price": round(final, 2),
        "stock_quantity": stock,
        "min_stock_level": min_s,
        "available_stock": max(0, stock - p.get("reserved", 0)),
        "stock_status": status,
        "supplier_id": str(p["supplier_id"]) if p.get("supplier_id") else None,
        "images": p.get("images") or [],
        "variants": p.get("variants") or [],
        "tags": p.get("tags") or [],
        "is_featured": p.get("is_featured", False),
        "is_best_seller": p.get("is_best_seller", False),
        "status": p.get("status", "active"),
        "intelligence_score": p.get("intelligence_score"),
        "demand_trend": p.get("demand_trend"),
        "predicted_demand_30d": p.get("predicted_demand_30d"),
        "created_at": p.get("created_at").isoformat() if p.get("created_at") else None,
    }


# ---------- Public / Customer product listing ----------
@router.get("/products", response_model=List[dict])
async def list_products(
    q: Optional[str] = None,
    category_id: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    featured: Optional[bool] = None,
    best_seller: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
):
    db = get_db()
    filt: dict = {"status": "active"}
    if q:
        filt["$text"] = {"$search": q}
    if category_id:
        filt["category_id"] = _to_oid(category_id, "category id")
    if brand:
        brand_list = [b.strip() for b in brand.split(",") if b.strip()]
        if len(brand_list) == 1:
            filt["brand"] = brand_list[0]
        elif brand_list:
            filt["brand"] = {"$in": brand_list}
    if min_price is not None or max_price is not None:
        price_f = {}
        if min_price is not None:
            price_f["$gte"] = min_price
        if max_price is not None:
            price_f["$lte"] = max_price
        filt["selling_price"] = price_f
    if featured is not None:
        filt["is_featured"] = featured
    if best_seller is not None:
        filt["is_best_seller"] = best_seller

    cursor = db.products.find(filt).skip(skip).limit(limit).sort("created_at", -1)
    return [_serialize_product(p) async for p in cursor]


@router.get("/brands")
async def list_brands():
    """Distinct active product brands, sorted alphabetically (A -> Z)."""
    db = get_db()
    brands = await db.products.distinct("brand", {"status": "active", "brand": {"$ne": None}})
    return sorted((b for b in brands if str(b).strip()), key=str.lower)


@router.get("/products/{product_id}")
async def get_product(product_id: str):
    db = get_db()
    p = await db.products.find_one({"_id": _to_oid(product_id)})
    if not p:
        raise HTTPException(404, "Product not found")
    return _serialize_product(p)


# ---------- Admin product management ----------
@router.post("/admin/products", response_model=dict)
async def create_product(
    body: ProductCreate,
    admin: dict = Depends(require_permission("products.create")),
):
    db = get_db()
    if await db.products.find_one({"sku": body.sku}):
        raise HTTPException(400, "SKU already exists")
    doc = body.model_dump()
    doc["slug"] = doc.get("slug") or _slug(doc["name"])
    if doc.get("category_id"):
        doc["category_id"] = await _resolve_category_id(db, doc["category_id"])
    else:
        doc["category_id"] = None
    if doc.get("supplier_id"):
        doc["supplier_id"] = _to_oid(doc["supplier_id"], "supplier id")
    doc["reserved"] = 0
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = doc["created_at"]
    result = await db.products.insert_one(doc)
    # also seed inventory
    await db.inventory.insert_one({
        "product_id": result.inserted_id,
        "warehouse_id": None,
        "quantity": doc["stock_quantity"],
        "reserved": 0,
        "min_level": doc["min_stock_level"],
        "updated_at": datetime.now(timezone.utc),
    })
    p = await db.products.find_one({"_id": result.inserted_id})
    return _serialize_product(p)


@router.patch("/admin/products/{product_id}")
async def update_product(
    product_id: str,
    body: ProductUpdate,
    admin: dict = Depends(require_permission("products.edit")),
):
    db = get_db()
    update = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "category_id" in update:
        if update["category_id"]:
            update["category_id"] = await _resolve_category_id(db, update["category_id"])
        else:
            update["category_id"] = None
    update["updated_at"] = datetime.now(timezone.utc)
    result = await db.products.update_one({"_id": _to_oid(product_id)}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    p = await db.products.find_one({"_id": ObjectId(product_id)})
    return _serialize_product(p)


@router.delete("/admin/products/{product_id}")
async def delete_product(
    product_id: str,
    admin: dict = Depends(require_permission("products.delete")),
):
    db = get_db()
    result = await db.products.update_one(
        {"_id": _to_oid(product_id)},
        {"$set": {"status": "deleted", "updated_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Product not found")
    return {"message": "Product deleted", "success": True}


# ---------- Product image upload ----------
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "products"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


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


@router.post("/admin/products/upload-image")
async def upload_product_image(
    request: Request,
    file: UploadFile = File(...),
    admin: dict = Depends(require_permission("products.create")),
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
    return {"url": f"{base}/uploads/products/{name}", "filename": name}


# ---------- Categories ----------
@router.get("/categories", response_model=List[dict])
async def list_categories():
    db = get_db()
    cats = [c async for c in db.categories.find({"status": "active"}).sort("order", 1)]
    # build tree
    by_id = {str(c["_id"]): {**c, "id": str(c["_id"]), "children": []} for c in cats}
    roots = []
    for c in by_id.values():
        pid = str(c.get("parent_id")) if c.get("parent_id") else None
        if pid and pid in by_id:
            by_id[pid]["children"].append(c)
        else:
            roots.append(c)
    def clean(node):
        return {
            "id": node["id"],
            "name": node.get("name"),
            "slug": node.get("slug"),
            "parent_id": str(node["parent_id"]) if node.get("parent_id") else None,
            "description": node.get("description"),
            "image": node.get("image"),
            "order": node.get("order", 0),
            "status": node.get("status"),
            "children": [clean(ch) for ch in node.get("children", [])],
        }
    return [clean(r) for r in roots]


async def _unique_slug(db, base: str) -> str:
    """Return a slug that does not collide with the global unique slug index."""
    candidate = base
    n = 2
    while await db.categories.find_one({"slug": candidate}):
        candidate = f"{base}-{n}"
        n += 1
    return candidate


@router.post("/admin/categories")
async def create_category(
    body: CategoryCreate,
    admin: dict = Depends(require_permission("categories.create")),
):
    db = get_db()
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Category name is required")

    parent_id = None
    if body.parent_id:
        try:
            parent_id = ObjectId(body.parent_id)
        except Exception:
            raise HTTPException(400, "Invalid parent category id")
        parent = await db.categories.find_one({"_id": parent_id, "status": {"$ne": "deleted"}})
        if not parent:
            raise HTTPException(404, "Parent category not found")

    sibling_filter = {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}
    sibling_filter["parent_id"] = parent_id
    if await db.categories.find_one(sibling_filter):
        raise HTTPException(400, "A category with this name already exists here")

    slug = body.slug or _slug(name)
    doc = {
        "name": name,
        "slug": await _unique_slug(db, slug),
        "parent_id": parent_id,
        "description": body.description,
        "image": body.image,
        "order": body.order,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.categories.insert_one(doc)
    return {"id": str(result.inserted_id), **doc}


@router.get("/admin/categories")
async def admin_list_categories(
    admin: dict = Depends(require_permission("categories.view")),
):
    db = get_db()
    cats = [c async for c in db.categories.find({"status": {"$ne": "deleted"}}).sort("order", 1)]
    return [
        {
            "id": str(c["_id"]),
            "name": c.get("name"),
            "slug": c.get("slug"),
            "parent_id": str(c["parent_id"]) if c.get("parent_id") else None,
            "description": c.get("description"),
            "image": c.get("image"),
            "order": c.get("order", 0),
            "status": c.get("status", "active"),
            "created_at": c.get("created_at").isoformat() if c.get("created_at") else None,
        }
        for c in cats
    ]


@router.delete("/admin/categories/{category_id}")
async def delete_category(
    category_id: str,
    admin: dict = Depends(require_permission("categories.delete")),
):
    db = get_db()
    oid = _to_oid(category_id, "category id")
    cat = await db.categories.find_one({"_id": oid, "status": {"$ne": "deleted"}})
    if not cat:
        raise HTTPException(404, "Category not found")

    # Collect the category and every nested subcategory (cascade).
    ids = [oid]
    queue = [oid]
    while queue:
        parent = queue.pop(0)
        children = [
            child["_id"]
            async for child in db.categories.find({"parent_id": parent, "status": {"$ne": "deleted"}})
        ]
        ids.extend(children)
        queue.extend(children)

    now = datetime.now(timezone.utc)
    await db.categories.update_many(
        {"_id": {"$in": ids}},
        {"$set": {"status": "deleted", "updated_at": now}},
    )
    return {"message": "Category deleted", "success": True, "deleted_count": len(ids)}
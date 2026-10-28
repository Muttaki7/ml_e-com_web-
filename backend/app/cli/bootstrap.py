"""One-time bootstrap for hosted deployments without shell access.

Runs before Uvicorn in the container entrypoint:
    python -m app.cli.bootstrap

Creates the Main Admin from BOOTSTRAP_ADMIN_* when the account does not exist,
and seeds a small catalog when BOOTSTRAP_DEMO_DATA=true and the products
collection is empty. It never deletes data and never overwrites an existing
account or catalog.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.constants import AdminRole, ROLE_PERMISSIONS
from app.core.database import close_db, connect_db, get_db
from app.core.security import hash_password

from app.cli.demo_data import CATEGORIES, PRODUCTS, demo_image

logger = logging.getLogger("bootstrap")


async def bootstrap_admin() -> None:
    email = settings.BOOTSTRAP_ADMIN_EMAIL.strip().lower()
    if not email:
        return

    db = get_db()
    existing = await db.admins.find_one({"email": email})
    if existing:
        logger.info("Bootstrap admin %s already exists; leaving it unchanged", email)
        return

    password = settings.BOOTSTRAP_ADMIN_PASSWORD
    if len(password) < 12:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters")

    now = datetime.now(timezone.utc)
    await db.admins.insert_one({
        "full_name": settings.BOOTSTRAP_ADMIN_NAME.strip() or "Store Owner",
        "email": email,
        "phone": "",
        "password_hash": hash_password(password),
        "role": AdminRole.MAIN_ADMIN,
        "permissions": ROLE_PERMISSIONS[AdminRole.MAIN_ADMIN],
        "two_factor_required": True,
        "two_factor": None,
        "is_main_admin": True,
        "status": "active",
        "failed_login_attempts": 0,
        "lockout_until": None,
        "must_change_password": False,
        "created_by": None,
        "created_at": now,
        "updated_at": now,
    })
    logger.info("Created bootstrap Main Admin %s (enroll 2FA after first login)", email)


async def bootstrap_demo_catalog() -> None:
    if not settings.BOOTSTRAP_DEMO_DATA:
        return
    db = get_db()
    if await db.products.count_documents({}) > 0:
        logger.info("Products already exist; skipping demo catalog")
        return

    now = datetime.now(timezone.utc)
    category_ids: dict[str, object] = {}
    for name, slug, children in CATEGORIES:
        root = await db.categories.find_one({"slug": slug})
        if not root:
            result = await db.categories.insert_one({
                "name": name,
                "slug": slug,
                "parent_id": None,
                "order": 0,
                "status": "active",
                "created_at": now,
            })
            root_id = result.inserted_id
        else:
            root_id = root["_id"]
        category_ids[name] = root_id
        for index, child in enumerate(children):
            child_slug = child.lower().replace(" ", "-").replace("'", "")
            child_doc = await db.categories.find_one({"slug": child_slug})
            if not child_doc:
                result = await db.categories.insert_one({
                    "name": child,
                    "slug": child_slug,
                    "parent_id": root_id,
                    "order": index,
                    "status": "active",
                    "created_at": now,
                })
                child_id = result.inserted_id
            else:
                child_id = child_doc["_id"]
            category_ids[child] = child_id

    for index, (name, root_cat, sub_cat, purchase, selling, stock, featured) in enumerate(PRODUCTS):
        slug = name.lower().replace(" ", "-").replace("'", "")[:60]
        product = {
            "name": name,
            "slug": slug,
            "sku": f"DEMO-{index + 1:04d}",
            "description": f"Quality {name} with fast local and international delivery.",
            "category_id": category_ids.get(sub_cat) or category_ids.get(root_cat),
            "brand": name.split()[0],
            "purchase_price": purchase,
            "selling_price": selling,
            "discount_percent": 0,
            "tax_percent": 0,
            "stock_quantity": stock,
            "min_stock_level": max(5, stock // 10),
            "reserved": 0,
            "images": [demo_image(name, index)],
            "variants": [],
            "tags": [root_cat.lower(), sub_cat.lower()],
            "is_featured": featured,
            "is_best_seller": featured,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        result = await db.products.insert_one(product)
        await db.inventory.insert_one({
            "product_id": result.inserted_id,
            "warehouse_id": None,
            "quantity": stock,
            "reserved": 0,
            "min_level": product["min_stock_level"],
            "updated_at": now,
        })

    logger.info("Inserted %d demo products", len(PRODUCTS))


async def bootstrap_demo_accounts() -> None:
    """Create fixed demo logins for a public review deployment.

    Only runs when DEMO_MODE is enabled. Leaving 2FA unenrolled is intentional:
    the demo accounts are meant to be used with one click and hold no real data.
    """
    if not settings.DEMO_MODE:
        return

    db = get_db()
    now = datetime.now(timezone.utc)

    admin_email = settings.DEMO_ADMIN_EMAIL.strip().lower()
    if admin_email and not await db.admins.find_one({"email": admin_email}):
        password = settings.DEMO_ADMIN_PASSWORD
        if len(password) < 12:
            raise SystemExit("DEMO_ADMIN_PASSWORD must be at least 12 characters")
        await db.admins.insert_one({
            "full_name": "Demo Admin",
            "email": admin_email,
            "phone": "",
            "password_hash": hash_password(password),
            "role": AdminRole.ADMIN,
            "permissions": ROLE_PERMISSIONS[AdminRole.ADMIN],
            "two_factor_required": False,
            "two_factor": None,
            "is_main_admin": False,
            "status": "active",
            "failed_login_attempts": 0,
            "lockout_until": None,
            "must_change_password": False,
            "created_by": None,
            "created_at": now,
            "updated_at": now,
        })
        logger.info("Created demo admin %s", admin_email)

    customer_email = settings.DEMO_CUSTOMER_EMAIL.strip().lower()
    if customer_email and not await db.customers.find_one({"email": customer_email}):
        await db.customers.insert_one({
            "full_name": "Demo Shopper",
            "email": customer_email,
            "phone": "",
            "password_hash": hash_password(settings.DEMO_CUSTOMER_PASSWORD),
            "status": "active",
            "addresses": [],
            "two_factor": None,
            "pending_2fa": None,
            "created_at": now,
            "updated_at": now,
        })
        logger.info("Created demo customer %s", customer_email)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not (
        settings.BOOTSTRAP_ADMIN_EMAIL
        or settings.BOOTSTRAP_DEMO_DATA
        or settings.DEMO_MODE
    ):
        return
    await connect_db()
    try:
        await bootstrap_admin()
        await bootstrap_demo_catalog()
        await bootstrap_demo_accounts()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())

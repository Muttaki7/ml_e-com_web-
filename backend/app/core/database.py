from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global client, db
    # tz_aware: BSON datetimes are otherwise returned naive, which breaks
    # comparisons against the timezone-aware datetimes this app stores.
    client = AsyncIOMotorClient(settings.MONGODB_URI, tz_aware=True)
    db = client[settings.MONGODB_DB]
    # Ensure indexes
    await _create_indexes()


async def close_db() -> None:
    global client
    if client:
        client.close()


def get_db() -> AsyncIOMotorDatabase:
    if db is None:
        raise RuntimeError("Database not connected")
    return db


async def _create_indexes() -> None:
    if db is None:
        return
    # Customers
    await db.customers.create_index("email", unique=True)
    await db.customers.create_index("phone")
    # Admins
    await db.admins.create_index("email", unique=True)
    await db.admins.create_index("role")
    # Products
    await db.products.create_index("sku", unique=True)
    await db.products.create_index("slug")
    await db.products.create_index([("name", "text"), ("description", "text")])
    await db.products.create_index("category_id")
    await db.products.create_index("status")
    # Categories
    await db.categories.create_index("slug", unique=True)
    await db.categories.create_index("parent_id")
    # Orders
    await db.orders.create_index("order_number", unique=True)
    await db.orders.create_index("customer_id")
    await db.orders.create_index("status")
    await db.orders.create_index("created_at")
    await db.orders.create_index("payment_status")
    # Inventory
    await db.inventory.create_index([("product_id", 1), ("warehouse_id", 1)], unique=True)
    await db.inventory.create_index("stock_status")
    # Suppliers
    await db.suppliers.create_index("email")
    # Audit
    await db.audit_logs.create_index("actor_id")
    await db.audit_logs.create_index("created_at")
    # Refresh tokens
    await db.refresh_tokens.create_index("token_jti", unique=True)
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
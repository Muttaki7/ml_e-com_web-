"""
Seed realistic multi-country demo data so ML & analytics dashboards show
meaningful trends. Run: cd backend && python -m scripts.seed
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberType
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings
from app.core.security import hash_password
from app.core.constants import ROLE_PERMISSIONS, AdminRole, OrderStatus, PaymentMethod, PaymentStatus

CATEGORIES = [
    {"name": "Electronics", "slug": "electronics", "children": ["Mobile Phones", "Laptops", "Accessories"]},
    {"name": "Fashion", "slug": "fashion", "children": ["Men's Clothing", "Women's Clothing", "Shoes"]},
    {"name": "Home & Living", "slug": "home-living", "children": ["Kitchen", "Furniture", "Decor"]},
    {"name": "Groceries", "slug": "groceries", "children": ["Rice & Flour", "Spices", "Snacks"]},
    {"name": "Beauty", "slug": "beauty", "children": ["Skincare", "Makeup"]},
]

PRODUCT_TEMPLATES = [
    ("Samsung Galaxy A55", "Electronics", "Mobile Phones", 320, 389, 45),
    ("Xiaomi Redmi Note 13", "Electronics", "Mobile Phones", 180, 229, 80),
    ("Acer Aspire 5 Laptop", "Electronics", "Laptops", 450, 549, 25),
    ("Anker PowerBank 20000mAh", "Electronics", "Accessories", 18, 24, 120),
    ("Men's Cotton Shirt", "Fashion", "Men's Clothing", 6, 9, 200),
    ("Women's Summer Dress", "Fashion", "Women's Clothing", 12, 18, 150),
    ("Sports Shoes Unisex", "Fashion", "Shoes", 9, 14, 90),
    ("Non-stick Fry Pan", "Home & Living", "Kitchen", 4, 7, 70),
    ("Jasmine Rice 10kg", "Groceries", "Rice & Flour", 18, 21, 300),
    ("Spicy Snack Mix", "Groceries", "Snacks", 0.35, 0.55, 500),
    ("Gentle Face Wash", "Beauty", "Skincare", 1.8, 2.99, 200),
    ("Matte Lipstick", "Beauty", "Makeup", 3.5, 5.5, 100),
]

# (country code, [cities])
MARKETS = [
    ("US", ["New York", "Los Angeles", "Chicago", "Houston"]),
    ("GB", ["London", "Manchester", "Birmingham"]),
    ("CA", ["Toronto", "Vancouver", "Montreal"]),
    ("AU", ["Sydney", "Melbourne", "Brisbane"]),
    ("DE", ["Berlin", "Munich", "Hamburg"]),
    ("IN", ["Mumbai", "Delhi", "Bangalore"]),
    ("BD", ["Dhaka", "Chattogram", "Sylhet"]),
    ("SG", ["Singapore"]),
    ("AE", ["Dubai", "Abu Dhabi"]),
    ("BR", ["São Paulo", "Rio de Janeiro"]),
]

_PHONE_POOL: dict[str, list[str]] = {}


def _demo_phone(region: str) -> str:
    """A valid E.164 mobile number for the market.

    Seeded numbers must satisfy the same libphonenumber validation the API
    applies, otherwise checkout rejects the customer's pre-filled phone.
    """
    pool = _PHONE_POOL.get(region)
    if pool is None:
        base = (
            phonenumbers.example_number_for_type(region, PhoneNumberType.MOBILE)
            or phonenumbers.example_number(region)
        )
        pool = []
        for offset in range(500):
            candidate = phonenumbers.PhoneNumber(
                country_code=base.country_code,
                national_number=base.national_number + offset,
            )
            if phonenumbers.is_valid_number(candidate):
                pool.append(phonenumbers.format_number(candidate, PhoneNumberFormat.E164))
            if len(pool) >= 25:
                break
        if not pool:
            pool = [phonenumbers.format_number(base, PhoneNumberFormat.E164)]
        _PHONE_POOL[region] = pool
    return random.choice(pool)


async def seed():
    # This script deletes collections. Never allow it to run against a
    # production deployment or a remote database.
    if settings.is_production:
        raise SystemExit("Refusing to seed demo data when APP_ENV is production")
    from urllib.parse import urlparse

    host = (urlparse(settings.MONGODB_URI).hostname or "").lower()
    if host not in {"localhost", "127.0.0.1", "::1"} and not os.getenv("ALLOW_REMOTE_SEED"):
        raise SystemExit(
            f"Refusing to seed non-local MongoDB host '{host}'. "
            "Set ALLOW_REMOTE_SEED=1 only if you are certain this is a disposable database."
        )

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    print("Clearing existing demo collections...")
    for col in ["admins", "customers", "categories", "products", "orders", "inventory", "audit_logs", "payments"]:
        await db[col].delete_many({})

    # Main Admin
    main_admin = {
        "full_name": "Main Administrator",
        "email": "admin@example.com",
        "phone": "+12025550101",
        "password_hash": hash_password("Admin@12345"),
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
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.admins.insert_one(main_admin)
    print("Main Admin: admin@example.com / Admin@12345  (enable 2FA after first login)")

    # Inventory Manager example
    inv_admin = {
        "full_name": "Robin Inventory",
        "email": "robin@example.com",
        "phone": "+12025550102",
        "password_hash": hash_password("Robin@12345"),
        "role": AdminRole.INVENTORY_MANAGER,
        "permissions": ROLE_PERMISSIONS[AdminRole.INVENTORY_MANAGER],
        "two_factor_required": True,
        "two_factor": None,
        "is_main_admin": False,
        "status": "active",
        "failed_login_attempts": 0,
        "created_by": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    await db.admins.insert_one(inv_admin)

    # Categories
    cat_map = {}  # name -> ObjectId
    for root in CATEGORIES:
        rdoc = {
            "name": root["name"],
            "slug": root["slug"],
            "parent_id": None,
            "order": 0,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
        }
        r = await db.categories.insert_one(rdoc)
        cat_map[root["name"]] = r.inserted_id
        for i, child in enumerate(root["children"]):
            cdoc = {
                "name": child,
                "slug": child.lower().replace(" ", "-").replace("'", ""),
                "parent_id": r.inserted_id,
                "order": i,
                "status": "active",
                "created_at": datetime.now(timezone.utc),
            }
            c = await db.categories.insert_one(cdoc)
            cat_map[child] = c.inserted_id
    print(f"Categories: {len(cat_map)}")

    # Products
    product_ids = []
    for name, root_cat, sub_cat, purchase, sell, stock in PRODUCT_TEMPLATES:
        # create a few variants by slight price/stock variation
        for i in range(3 if "Phone" in name or "Laptop" in name else 1):
            p_name = name if i == 0 else f"{name} (Var {i+1})"
            sku = f"SKU-{abs(hash(p_name)) % 100000:05d}"
            doc = {
                "name": p_name,
                "slug": p_name.lower().replace(" ", "-")[:60],
                "sku": sku,
                "description": f"Quality {p_name} with fast local and international delivery.",
                "category_id": cat_map.get(sub_cat) or cat_map.get(root_cat),
                "brand": name.split()[0],
                "purchase_price": purchase + i,
                "selling_price": sell + i * 1.5,
                "discount_percent": random.choice([0, 5, 10, 15]),
                "tax_percent": 0,
                "stock_quantity": stock - i * 5,
                "min_stock_level": max(5, stock // 10),
                "reserved": 0,
                "images": [],
                "variants": [],
                "tags": [root_cat.lower(), sub_cat.lower()],
                "is_featured": random.random() > 0.7,
                "is_best_seller": random.random() > 0.8,
                "status": "active",
                "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(10, 120)),
                "updated_at": datetime.now(timezone.utc),
            }
            res = await db.products.insert_one(doc)
            product_ids.append(res.inserted_id)
            await db.inventory.insert_one({
                "product_id": res.inserted_id,
                "warehouse_id": None,
                "quantity": doc["stock_quantity"],
                "reserved": 0,
                "min_level": doc["min_stock_level"],
                "updated_at": datetime.now(timezone.utc),
            })
    print(f"Products: {len(product_ids)}")

    # Customers across multiple countries
    customer_ids = []
    for i in range(80):
        code, cities = random.choice(MARKETS)
        city = random.choice(cities)
        phone = _demo_phone(code)
        doc = {
            "full_name": f"Customer {i+1}",
            "email": f"customer{i+1}@example.com",
            "phone": phone,
            "password_hash": hash_password("Customer@123"),
            "status": "active",
            "addresses": [{
                "full_name": f"Customer {i+1}",
                "phone": phone,
                "country": code,
                "state": city,
                "city": city,
                "address_line": f"{random.randint(1,200)} Main Street",
                "postal_code": f"{random.randint(10000,99999)}",
            }],
            "two_factor": None,
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(5, 200)),
            "updated_at": datetime.now(timezone.utc),
        }
        r = await db.customers.insert_one(doc)
        customer_ids.append(r.inserted_id)
    print(f"Customers: {len(customer_ids)}")

    # Orders (last 90 days) – enough for ML trends
    products = await db.products.find({"status": "active"}).to_list(100)
    order_count = 0
    store_country = settings.STORE_COUNTRY
    for day_offset in range(90, 0, -1):
        day = datetime.now(timezone.utc) - timedelta(days=day_offset)
        n_orders = random.randint(3, 12)
        for _ in range(n_orders):
            cust = random.choice(customer_ids)
            n_items = random.randint(1, 4)
            chosen = random.sample(products, min(n_items, len(products)))
            items = []
            subtotal = 0.0
            for p in chosen:
                qty = random.randint(1, 3)
                unit = p["selling_price"] * (1 - p.get("discount_percent", 0) / 100)
                line = unit * qty
                subtotal += line
                items.append({
                    "product_id": p["_id"],
                    "name": p["name"],
                    "sku": p["sku"],
                    "quantity": qty,
                    "unit_price": round(unit, 2),
                    "line_total": round(line, 2),
                    "purchase_price": p.get("purchase_price", 0),
                })
            code, cities = random.choice(MARKETS)
            delivery = (5.0 if code == store_country else 25.0) if subtotal < 50 else 0.0
            total = subtotal + delivery
            method = random.choices(
                [PaymentMethod.COD, PaymentMethod.CARD, PaymentMethod.PAYPAL],
                weights=[0.45, 0.4, 0.15],
            )[0]
            status = random.choices(
                [OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.PENDING, OrderStatus.CANCELLED],
                weights=[0.65, 0.15, 0.12, 0.08],
            )[0]
            pay_status = PaymentStatus.COD_COLLECTED if method == PaymentMethod.COD and status == OrderStatus.DELIVERED else (
                PaymentStatus.PAID if status == OrderStatus.DELIVERED else PaymentStatus.PENDING
            )
            city = random.choice(cities)
            order = {
                "order_number": f"{settings.ORDER_NUMBER_PREFIX}{day.strftime('%Y%m%d')}{random.randint(10000,99999)}",
                "customer_id": cust,
                "items": items,
                "subtotal": round(subtotal, 2),
                "discount": 0,
                "delivery_charge": delivery,
                "tax": 0,
                "total": round(total, 2),
                "currency": settings.CURRENCY,
                "shipping_address": {
                    "full_name": "Demo",
                    "phone": _demo_phone(code),
                    "country": code,
                    "state": city,
                    "city": city,
                    "address_line": "Demo address",
                },
                "payment_method": method,
                "payment_status": pay_status,
                "status": status,
                "created_at": day + timedelta(hours=random.randint(0, 23)),
                "updated_at": day,
                "history": [{"status": status, "at": day}],
            }
            await db.orders.insert_one(order)
            order_count += 1
    print(f"Orders: {order_count}")

    print("\nSeed complete.")
    print("Login (admin): admin@example.com / Admin@12345")
    print("Login (customer example): customer1@example.com / Customer@123")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())

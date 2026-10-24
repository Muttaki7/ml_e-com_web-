"""Live security smoke tests for a running backend (localhost:8000).

Covers refresh-token misuse, upload spoofing, payment-callback forgery,
oversell races and login rate limiting. Uses local demo accounts and Mongo.
"""
import asyncio
import base64
import hashlib
import hmac
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.core.config import settings  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
ROOT = Path(__file__).resolve().parents[1]
mongo = MongoClient("mongodb://localhost:27017")
db = mongo["global_ecommerce_erp"]
client = httpx.Client(timeout=30)
results = []


def check(name, cond, extra=""):
    results.append((name, cond))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))


def sign(raw: bytes) -> str:
    return hmac.new(settings.PAYMENT_CALLBACK_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def main():
    r = client.post(
        f"{BASE}/auth/customer/login",
        json={"email": "customer1@example.com", "password": "Customer@123"},
    )
    check("customer login works", r.status_code == 200, f"{r.status_code} {r.text[:100]}")
    if r.status_code != 200:
        return summary()
    tokens = r.json()
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    r = client.get(f"{BASE}/orders/my", headers={"Authorization": f"Bearer {refresh}"})
    check("refresh token rejected as bearer access", r.status_code == 401, f"{r.status_code}")

    r = client.get(f"{BASE}/orders/my", headers={"Authorization": f"Bearer {access}"})
    check("access token still works", r.status_code == 200, f"{r.status_code}")

    r = client.post(
        f"{BASE}/auth/admin/login",
        json={"email": "admin@example.com", "password": "Admin@12345"},
    )
    check("admin login works", r.status_code == 200, f"{r.status_code} {r.text[:100]}")
    if r.status_code != 200:
        return summary()
    admin_access = r.json()["access_token"]
    r = client.get(f"{BASE}/auth/admin/me", headers={"Authorization": f"Bearer {admin_access}"})
    check("admin profile works", r.status_code == 200, f"{r.status_code}")

    r = client.post(
        f"{BASE}/admin/products/upload-image",
        headers={"Authorization": f"Bearer {admin_access}"},
        files={"file": ("evil.png", b"<html><script>alert(1)</script></html>", "image/png")},
    )
    check("HTML disguised as PNG rejected", r.status_code == 400, f"{r.status_code}")

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII="
    )
    r = client.post(
        f"{BASE}/admin/products/upload-image",
        headers={"Authorization": f"Bearer {admin_access}"},
        files={"file": ("photo.html", png, "text/html")},
    )
    check("PNG with spoofed text/html MIME rejected", r.status_code == 400, f"{r.status_code}")
    r = client.post(
        f"{BASE}/admin/products/upload-image",
        headers={"Authorization": f"Bearer {admin_access}"},
        files={"file": ("photo.html", png, "image/png")},
    )
    safe_name = r.json().get("filename", "") if r.status_code == 200 else ""
    check(
        "valid PNG gets safe .png extension",
        r.status_code == 200 and safe_name.endswith(".png"),
        f"{r.status_code} {r.text[:100]}",
    )
    if safe_name:
        (ROOT / "uploads" / "products" / safe_name).unlink(missing_ok=True)

    cust = db.customers.find_one({"email": "customer1@example.com"})
    oid = ObjectId()
    test_number = f"TEST{oid}"
    now = datetime.now(timezone.utc)
    db.orders.insert_one({
        "_id": oid, "order_number": test_number, "customer_id": cust["_id"],
        "items": [{
            "product_id": ObjectId(), "name": "Test item", "sku": "TEST",
            "quantity": 1, "unit_price": 10.0, "line_total": 10.0, "purchase_price": 1.0,
        }],
        "subtotal": 10.0, "discount": 0.0, "delivery_charge": 0.0, "tax": 0.0,
        "total": 10.0, "currency": "USD",
        "shipping_address": {
            "full_name": "Test", "phone": "+14155552671", "country": "US",
            "city": "NYC", "state": "NY", "address_line": "1 Main St", "postal_code": "10001",
        },
        "payment_method": "card", "payment_status": "pending", "status": "pending",
        "created_at": now, "updated_at": now, "history": [], "notes": None,
    })
    try:
        payload = {
            "transaction_id": f"TX{oid}", "order_id": str(oid),
            "status": "success", "amount": 10.0,
        }
        r = client.post(f"{BASE}/payments/card/callback", json=payload)
        check("unsigned callback rejected", r.status_code in (401, 403), f"{r.status_code} {r.text[:100]}")

        raw = json.dumps(payload, separators=(",", ":")).encode()
        headers = {
            "Content-Type": "application/json",
            "X-Payment-Signature": f"sha256={sign(raw)}",
        }
        r = client.post(f"{BASE}/payments/card/callback", content=raw, headers=headers)
        check("signed valid callback accepted", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        check("order marked paid", (db.orders.find_one({"_id": oid}) or {}).get("payment_status") == "paid")

        bad = dict(payload, amount=999.0)
        raw_bad = json.dumps(bad, separators=(",", ":")).encode()
        r = client.post(
            f"{BASE}/payments/card/callback", content=raw_bad,
            headers={"Content-Type": "application/json", "X-Payment-Signature": sign(raw_bad)},
        )
        check("signed wrong amount rejected", r.status_code == 400, f"{r.status_code}")

        downgrade = dict(payload, status="failed", transaction_id=f"TX{oid}B")
        raw_down = json.dumps(downgrade, separators=(",", ":")).encode()
        r = client.post(
            f"{BASE}/payments/card/callback", content=raw_down,
            headers={"Content-Type": "application/json", "X-Payment-Signature": sign(raw_down)},
        )
        still = (db.orders.find_one({"_id": oid}) or {}).get("payment_status")
        check("paid order cannot be downgraded", r.status_code == 200 and still == "paid", f"{r.status_code} {still}")

        raw_wp = json.dumps(payload, separators=(",", ":")).encode()
        r = client.post(
            f"{BASE}/payments/paypal/callback", content=raw_wp,
            headers={"Content-Type": "application/json", "X-Payment-Signature": sign(raw_wp)},
        )
        check("provider/order mismatch rejected", r.status_code == 400, f"{r.status_code}")
    finally:
        db.orders.delete_one({"_id": oid})
        db.payments.delete_many({"order_id": oid})
        (ROOT / "uploads" / "invoices" / f"INV-{test_number}.pdf").unlink(missing_ok=True)

    po = ObjectId()
    db.products.insert_one({
        "_id": po, "name": "Security Race Test", "slug": f"sec-race-{po}",
        "sku": f"SEC-{str(po)[-8:]}", "description": "temporary", "category_id": None,
        "brand": "Test", "purchase_price": 1.0, "selling_price": 10.0,
        "discount_percent": 0, "tax_percent": 0, "stock_quantity": 1,
        "min_stock_level": 0, "reserved": 0, "images": [], "variants": [], "tags": [],
        "is_featured": False, "is_best_seller": False, "status": "active",
        "created_at": now, "updated_at": now,
    })
    order_ids = []
    try:
        checkout_body = {
            "items": [{"product_id": str(po), "quantity": 1}],
            "shipping_address": {
                "full_name": "Race Test", "phone": "+14155552671", "country": "US",
                "city": "NYC", "state": "NY", "address_line": "1 Main St", "postal_code": "10001",
            },
            "payment_method": "cod",
        }

        async def race():
            async with httpx.AsyncClient(timeout=90) as ac:
                h = {"Authorization": f"Bearer {access}"}
                return await asyncio.gather(
                    ac.post(f"{BASE}/orders/checkout", json=checkout_body, headers=h),
                    ac.post(f"{BASE}/orders/checkout", json=checkout_body, headers=h),
                )

        rs = asyncio.run(race())
        codes = sorted(x.status_code for x in rs)
        check(
            "concurrent checkout prevents oversell", codes == [200, 400],
            str([(x.status_code, x.text[:80]) for x in rs]),
        )
        winner = next((x for x in rs if x.status_code == 200), None)
        if winner:
            win = winner.json()
            order_ids.append(ObjectId(win["order_id"]))
            r = client.patch(
                f"{BASE}/admin/orders/{win['order_id']}/status",
                params={"status": "cancelled"},
                headers={"Authorization": f"Bearer {admin_access}"},
            )
            prod = db.products.find_one({"_id": po}) or {}
            check(
                "cancellation releases reservation",
                r.status_code == 200 and prod.get("reserved") == 0,
                f"{r.status_code} reserved={prod.get('reserved')}",
            )
        else:
            check("cancellation releases reservation", False, "no successful checkout")
    finally:
        for oid2 in order_ids:
            o = db.orders.find_one({"_id": oid2}) or {}
            db.orders.delete_one({"_id": oid2})
            if o.get("order_number"):
                (ROOT / "uploads" / "invoices" / f"INV-{o['order_number']}.pdf").unlink(missing_ok=True)
        db.orders.delete_many({"items.product_id": po})
        db.products.delete_one({"_id": po})

    po2 = ObjectId()
    db.products.insert_one({
        "_id": po2, "name": "Security Delivery Test", "slug": f"sec-deliver-{po2}",
        "sku": f"DEL-{str(po2)[-8:]}", "description": "temporary", "category_id": None,
        "brand": "Test", "purchase_price": 1.0, "selling_price": 10.0,
        "discount_percent": 0, "tax_percent": 0, "stock_quantity": 5,
        "min_stock_level": 0, "reserved": 0, "images": [], "variants": [], "tags": [],
        "is_featured": False, "is_best_seller": False, "status": "active",
        "created_at": now, "updated_at": now,
    })
    delivered_order = None
    try:
        body = dict(checkout_body, items=[{"product_id": str(po2), "quantity": 2}])
        r = client.post(f"{BASE}/orders/checkout", json=body,
                        headers={"Authorization": f"Bearer {access}"})
        check("checkout reserves stock", r.status_code == 200, f"{r.status_code} {r.text[:100]}")
        if r.status_code == 200:
            delivered_order = ObjectId(r.json()["order_id"])
            prod = db.products.find_one({"_id": po2}) or {}
            check("reservation recorded", prod.get("reserved") == 2, f"reserved={prod.get('reserved')}")
            r = client.patch(
                f"{BASE}/admin/orders/{delivered_order}/status",
                params={"status": "delivered"},
                headers={"Authorization": f"Bearer {admin_access}"},
            )
            prod = db.products.find_one({"_id": po2}) or {}
            order_doc = db.orders.find_one({"_id": delivered_order}) or {}
            check(
                "delivery commits stock and clears reservation",
                r.status_code == 200 and prod.get("stock_quantity") == 3 and prod.get("reserved") == 0,
                f"{r.status_code} stock={prod.get('stock_quantity')} reserved={prod.get('reserved')}",
            )
            check("delivery is idempotent-flagged", order_doc.get("stock_committed") is True)
        else:
            check("reservation recorded", False, "checkout failed")
            check("delivery commits stock and clears reservation", False, "checkout failed")
            check("delivery is idempotent-flagged", False, "checkout failed")
    finally:
        if delivered_order:
            o = db.orders.find_one({"_id": delivered_order}) or {}
            db.orders.delete_one({"_id": delivered_order})
            if o.get("order_number"):
                (ROOT / "uploads" / "invoices" / f"INV-{o['order_number']}.pdf").unlink(missing_ok=True)
        db.products.delete_one({"_id": po2})

    codes = []
    for _ in range(12):
        r = client.post(
            f"{BASE}/auth/customer/login",
            json={"email": "nobody@example.com", "password": "WrongPass123"},
        )
        codes.append(r.status_code)
    check("login rate limiting returns 429", 429 in codes, str(codes))

    return summary()


def summary():
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed}/{len(results)} security checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

from typing import List, Optional
from datetime import datetime, timezone
import secrets
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from bson import ObjectId
from pymongo import ReturnDocument
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.config import settings
from app.core.constants import OrderStatus, PaymentStatus, PaymentMethod
from app.api.deps import get_current_customer, get_current_admin, require_permission
from app.services.audit_service import log_action
from app.services.invoice_service import generate_order_invoice, ensure_order_invoice
from app.api.v1.settings import (
    get_delivery_charge, get_store_meta, get_settings_doc, enabled_payment_methods,
)
from app.schemas.common import PhoneMixin, CountryMixin

router = APIRouter(tags=["Orders"])


def _to_oid(value: str, label: str = "id") -> ObjectId:
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


class OrderItemIn(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1, le=1000)
    variant_sku: Optional[str] = None


class AddressIn(PhoneMixin, CountryMixin, BaseModel):
    full_name: str
    phone: str
    country: str
    city: str
    state: Optional[str] = None
    address_line: str
    postal_code: Optional[str] = None


class CheckoutIn(BaseModel):
    items: List[OrderItemIn] = Field(..., min_length=1, max_length=50)
    shipping_address: AddressIn
    payment_method: PaymentMethod
    coupon_code: Optional[str] = None
    notes: Optional[str] = None


def _order_number() -> str:
    now = datetime.now(timezone.utc)
    return f"{settings.ORDER_NUMBER_PREFIX}{now.strftime('%Y%m%d')}{secrets.randbelow(10**8):08d}"


@router.post("/orders/checkout")
async def checkout(
    body: CheckoutIn,
    customer: dict = Depends(get_current_customer),
):
    db = get_db()
    # Only methods the store has enabled may be used at checkout
    settings_doc = await get_settings_doc()
    allowed = {m.get("id") for m in enabled_payment_methods(settings_doc)}
    if body.payment_method.value not in allowed:
        raise HTTPException(400, "Payment method not available in this store")

    items = []
    subtotal = 0.0
    reserved: list[tuple[ObjectId, int]] = []
    try:
        for it in body.items:
            oid = _to_oid(it.product_id, "product id")
            # Reserve atomically: the availability check and the increment are
            # one operation, so concurrent checkouts cannot oversell.
            p = await db.products.find_one_and_update(
                {
                    "_id": oid,
                    "status": "active",
                    "$expr": {
                        "$gte": [
                            {
                                "$subtract": [
                                    {"$ifNull": ["$stock_quantity", 0]},
                                    {"$ifNull": ["$reserved", 0]},
                                ]
                            },
                            it.quantity,
                        ]
                    },
                },
                {"$inc": {"reserved": it.quantity}},
                return_document=ReturnDocument.AFTER,
            )
            if not p:
                existing = await db.products.find_one({"_id": oid, "status": "active"})
                if not existing:
                    raise HTTPException(400, f"Product {it.product_id} not found")
                raise HTTPException(400, f"Insufficient stock for {existing.get('name')}")
            reserved.append((oid, it.quantity))
            unit = p.get("selling_price", 0) * (1 - p.get("discount_percent", 0) / 100)
            line = unit * it.quantity
            subtotal += line
            items.append({
                "product_id": p["_id"],
                "name": p.get("name"),
                "sku": p.get("sku"),
                "quantity": it.quantity,
                "unit_price": round(unit, 2),
                "line_total": round(line, 2),
                "purchase_price": p.get("purchase_price", 0),
            })

        delivery_charge = await get_delivery_charge(subtotal, body.shipping_address.country)
        discount = 0.0
        total = subtotal + delivery_charge - discount

        payment_status = PaymentStatus.COD_PENDING if body.payment_method == PaymentMethod.COD else PaymentStatus.PENDING
        store_meta = await get_store_meta()

        order = {
            "order_number": _order_number(),
            "customer_id": ObjectId(customer["id"]),
            "items": items,
            "subtotal": round(subtotal, 2),
            "discount": discount,
            "delivery_charge": delivery_charge,
            "tax": 0.0,
            "total": round(total, 2),
            "currency": store_meta["currency"],
            "shipping_address": body.shipping_address.model_dump(),
            "payment_method": body.payment_method,
            "payment_status": payment_status,
            "status": OrderStatus.PENDING,
            "notes": body.notes,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "history": [{"status": OrderStatus.PENDING, "at": datetime.now(timezone.utc), "by": "customer"}],
        }
        result = await db.orders.insert_one(order)
    except Exception:
        # Never leave stock reserved for an order that was not created.
        for oid, qty in reserved:
            await db.products.update_one({"_id": oid}, {"$inc": {"reserved": -qty}})
        raise

    await log_action(customer["id"], "customer", "order.created", "order", str(result.inserted_id))

    # Generate and store the .pdf invoice on device (uploads/invoices/)
    try:
        await generate_order_invoice(str(result.inserted_id))
        has_invoice = True
    except Exception:
        has_invoice = False

    # For COD we keep status pending; for mobile money return payment initiation info
    response = {
        "order_id": str(result.inserted_id),
        "order_number": order["order_number"],
        "total": order["total"],
        "payment_method": body.payment_method,
        "payment_status": payment_status,
        "status": OrderStatus.PENDING,
        "has_invoice": has_invoice,
    }
    if body.payment_method != PaymentMethod.COD:
        response["payment_init"] = {
            "message": f"Initiate {body.payment_method} payment using merchant credentials",
            "callback_url": f"/api/v1/payments/{body.payment_method}/callback",
        }
    return response


@router.get("/orders/my")
async def my_orders(
    customer: dict = Depends(get_current_customer),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_db()
    cursor = db.orders.find({"customer_id": ObjectId(customer["id"])}).sort("created_at", -1).skip(skip).limit(limit)
    out = []
    async for o in cursor:
        out.append({
            "id": str(o["_id"]),
            "order_number": o.get("order_number"),
            "total": o.get("total"),
            "status": o.get("status"),
            "payment_status": o.get("payment_status"),
            "payment_method": o.get("payment_method"),
            "created_at": o["created_at"].isoformat() if o.get("created_at") else None,
            "item_count": len(o.get("items") or []),
            "items": [
                {
                    "name": it.get("name"),
                    "sku": it.get("sku"),
                    "quantity": it.get("quantity"),
                    "unit_price": it.get("unit_price"),
                    "line_total": it.get("line_total"),
                }
                for it in (o.get("items") or [])
            ],
            "has_invoice": bool(o.get("invoice_generated_at")),
        })
    return out


@router.get("/orders/my/{order_id}/invoice")
async def download_my_invoice(
    order_id: str,
    customer: dict = Depends(get_current_customer),
):
    db = get_db()
    order = await db.orders.find_one(
        {"_id": _to_oid(order_id), "customer_id": ObjectId(customer["id"])}
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    path = await ensure_order_invoice(str(order["_id"]))
    number = order.get("order_number") or str(order["_id"])
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"INV-{number}.pdf",
    )


@router.get("/admin/orders")
async def admin_list_orders(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_permission("orders.view")),
):
    db = get_db()
    filt = {}
    if status:
        filt["status"] = status
    if payment_status:
        filt["payment_status"] = payment_status
    cursor = db.orders.find(filt).sort("created_at", -1).skip(skip).limit(limit)
    out = []
    async for o in cursor:
        out.append({
            "id": str(o["_id"]),
            "order_number": o.get("order_number"),
            "customer_id": str(o.get("customer_id")),
            "total": o.get("total"),
            "status": o.get("status"),
            "payment_status": o.get("payment_status"),
            "payment_method": o.get("payment_method"),
            "created_at": o["created_at"].isoformat() if o.get("created_at") else None,
            "has_invoice": bool(o.get("invoice_generated_at")),
        })
    return out


@router.get("/admin/orders/{order_id}/invoice")
async def download_admin_invoice(
    order_id: str,
    admin: dict = Depends(require_permission("orders.view")),
):
    db = get_db()
    order = await db.orders.find_one({"_id": _to_oid(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    path = await ensure_order_invoice(str(order["_id"]))
    number = order.get("order_number") or str(order["_id"])
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"INV-{number}.pdf",
    )


@router.patch("/admin/orders/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: OrderStatus,
    admin: dict = Depends(require_permission("orders.edit")),
):
    db = get_db()
    order = await db.orders.find_one({"_id": _to_oid(order_id)})
    if not order:
        raise HTTPException(404, "Order not found")

    now = datetime.now(timezone.utc)
    stock_flags = {}
    if (
        status == OrderStatus.DELIVERED
        and not order.get("stock_committed")
        and not order.get("stock_released")
    ):
        # Delivered: convert the reservation into a real stock decrement.
        for it in order.get("items") or []:
            qty = it.get("quantity", 0)
            await db.products.update_one(
                {"_id": it["product_id"]},
                [{"$set": {
                    "stock_quantity": {"$max": [0, {"$subtract": [{"$ifNull": ["$stock_quantity", 0]}, qty]}]},
                    "reserved": {"$max": [0, {"$subtract": [{"$ifNull": ["$reserved", 0]}, qty]}]},
                }}],
            )
        stock_flags = {"stock_committed": True, "stock_released": True}
    elif status == OrderStatus.CANCELLED and not order.get("stock_released"):
        # Cancelled: return the reserved units to available stock.
        for it in order.get("items") or []:
            qty = it.get("quantity", 0)
            await db.products.update_one(
                {"_id": it["product_id"]},
                [{"$set": {
                    "reserved": {"$max": [0, {"$subtract": [{"$ifNull": ["$reserved", 0]}, qty]}]},
                }}],
            )
        stock_flags = {"stock_released": True}

    await db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {
            "$set": {"status": status, "updated_at": now, **stock_flags},
            "$push": {"history": {"status": status, "at": now, "by": admin["id"]}},
        },
    )
    # On delivered for COD → mark collected
    if status == OrderStatus.DELIVERED and order.get("payment_method") == PaymentMethod.COD:
        await db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {"payment_status": PaymentStatus.COD_COLLECTED}},
        )
    await log_action(admin["id"], "admin", "order.status_updated", "order", order_id, {"status": status})

    # Refresh the stored .pdf invoice so the latest status message is included
    from app.services.invoice_service import regenerate_order_invoice
    await regenerate_order_invoice(order_id)

    return {"message": "Status updated", "status": status}
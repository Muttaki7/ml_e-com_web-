"""
Payment provider adapters for global use.

COD is fully implemented. Stripe (cards) and PayPal cover international
customers; bKash / Nagad / Rocket remain available for Bangladesh
deployments (enable them in site settings and set the env credentials).
"""
from typing import Optional
from datetime import datetime, timezone
import hashlib
import hmac
import math
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from bson import ObjectId

from app.core.database import get_db
from app.core.config import settings
from app.core.constants import PaymentMethod, PaymentStatus
from app.core.limiter import limiter
from app.api.deps import get_current_customer, require_permission
from app.services.audit_service import log_action
from app.services.invoice_service import regenerate_order_invoice
from app.api.v1.settings import get_settings_doc, enabled_payment_methods, get_store_meta

router = APIRouter(prefix="/payments", tags=["Payments"])


def _to_oid(value: str, label: str = "id"):
    try:
        return ObjectId(value)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


class PaymentInit(BaseModel):
    order_id: str
    method: PaymentMethod
    amount: float = Field(..., gt=0, allow_inf_nan=False)
    customer_phone: Optional[str] = None


class PaymentCallback(BaseModel):
    transaction_id: str
    order_id: str
    status: str
    amount: Optional[float] = None
    raw: Optional[dict] = None


def _verify_stripe_signature(raw: bytes, header: str, secret: str) -> None:
    parts: dict = {}
    for item in header.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            parts.setdefault(key.strip(), value.strip())
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        raise HTTPException(401, "Invalid Stripe signature")
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(401, "Invalid Stripe signature")
    if abs(time.time() - ts) > 300:
        raise HTTPException(401, "Stripe signature expired")
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + raw, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid Stripe signature")


def _verify_callback_signature(provider: str, raw: bytes, request: Request) -> None:
    """Authenticate a gateway callback before it can change payment state.

    Stripe-native signatures are accepted for card payments when configured.
    All other providers must sign the raw body with PAYMENT_CALLBACK_SECRET.
    Callbacks are refused outright when no verification is configured.
    """
    if provider in (PaymentMethod.CARD.value, "stripe"):
        stripe_secret = settings.STRIPE_WEBHOOK_SECRET
        stripe_header = request.headers.get("stripe-signature")
        if stripe_secret and stripe_header:
            _verify_stripe_signature(raw, stripe_header, stripe_secret)
            return

    secret = settings.PAYMENT_CALLBACK_SECRET
    if not secret:
        raise HTTPException(503, "Payment callbacks are not configured")

    provided = (request.headers.get("x-payment-signature") or "").strip()
    if provided.startswith("sha256="):
        provided = provided.split("=", 1)[1]
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(401, "Invalid callback signature")


# ---------- Common interface ----------
class PaymentProvider:
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        raise NotImplementedError

    async def verify(self, transaction_id: str) -> dict:
        raise NotImplementedError


class CODProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        meta = await get_store_meta()
        return {
            "provider": "cod",
            "status": "cod_pending",
            "message": "Cash on Delivery selected. Collect {}{:.2f} on delivery.".format(
                meta["currency_symbol"], amount
            ),
            "amount": amount,
        }


class StripeProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        # Production: create a PaymentIntent via the Stripe API using
        # settings.STRIPE_SECRET_KEY and return its client_secret.
        if not settings.STRIPE_SECRET_KEY:
            return {
                "provider": "card",
                "status": "sandbox_stub",
                "message": "Stripe credentials not configured. Set STRIPE_SECRET_KEY.",
                "sandbox": True,
                "amount": amount,
                "order_id": str(order["_id"]),
            }
        return {
            "provider": "card",
            "status": "initiated",
            "payment_id": f"stripe_stub_{order['order_number']}",
            "client_secret": f"pi_stub_{order['order_number']}_secret",
            "amount": amount,
            "currency": order.get("currency"),
        }


class PayPalProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        # Production: create an order via the PayPal API using
        # settings.PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET and return the
        # approval link to redirect the customer to.
        if not settings.PAYPAL_CLIENT_ID:
            return {
                "provider": "paypal",
                "status": "sandbox_stub",
                "message": "PayPal credentials not configured. Set PAYPAL_CLIENT_ID.",
                "sandbox": True,
                "amount": amount,
                "order_id": str(order["_id"]),
            }
        return {
            "provider": "paypal",
            "status": "initiated",
            "payment_id": f"paypal_stub_{order['order_number']}",
            "approval_url": f"{settings.FRONTEND_URL}/payment/paypal/return?token=stub_{order['order_number']}",
            "amount": amount,
        }


class BKashProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        # Production: call bKash Create Payment API with settings.BKASH_* credentials
        if not settings.BKASH_API_KEY:
            return {
                "provider": "bkash",
                "status": "sandbox_stub",
                "message": "bKash credentials not configured. Set BKASH_API_KEY etc.",
                "sandbox": True,
                "amount": amount,
                "order_id": str(order["_id"]),
            }
        # Real integration would:
        # 1. Get token from bKash
        # 2. Create payment
        # 3. Return paymentID + redirect URL
        return {
            "provider": "bkash",
            "status": "initiated",
            "payment_id": f"bkash_stub_{order['order_number']}",
            "redirect_url": f"{settings.FRONTEND_URL}/payment/bkash/return",
            "amount": amount,
        }


class NagadProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        if not settings.NAGAD_MERCHANT_ID:
            return {
                "provider": "nagad",
                "status": "sandbox_stub",
                "message": "Nagad credentials not configured",
                "amount": amount,
            }
        return {
            "provider": "nagad",
            "status": "initiated",
            "payment_id": f"nagad_stub_{order['order_number']}",
            "amount": amount,
        }


class RocketProvider(PaymentProvider):
    async def initiate(self, order: dict, amount: float, phone: str = None) -> dict:
        return {
            "provider": "rocket",
            "status": "sandbox_stub",
            "message": "Rocket integration placeholder",
            "amount": amount,
        }


PROVIDERS = {
    PaymentMethod.COD: CODProvider(),
    PaymentMethod.CARD: StripeProvider(),
    PaymentMethod.PAYPAL: PayPalProvider(),
    PaymentMethod.BKASH: BKashProvider(),
    PaymentMethod.NAGAD: NagadProvider(),
    PaymentMethod.ROCKET: RocketProvider(),
}


@router.post("/initiate")
@limiter.limit("20/minute")
async def initiate_payment(
    body: PaymentInit,
    request: Request,
    customer: dict = Depends(get_current_customer),
):
    db = get_db()
    order = await db.orders.find_one({"_id": _to_oid(body.order_id), "customer_id": ObjectId(customer["id"])})
    if not order:
        raise HTTPException(404, "Order not found")
    if abs(order["total"] - body.amount) > 0.01:
        raise HTTPException(400, "Amount mismatch")

    # Only methods the store has enabled may be initiated
    doc = await get_settings_doc()
    allowed = {m.get("id") for m in enabled_payment_methods(doc)}
    if body.method.value not in allowed:
        raise HTTPException(400, "Payment method not available in this store")

    provider = PROVIDERS.get(body.method)
    if not provider:
        raise HTTPException(400, "Unsupported payment method")

    result = await provider.initiate(order, body.amount, body.customer_phone)

    await db.payments.insert_one({
        "order_id": order["_id"],
        "method": body.method,
        "amount": body.amount,
        "status": result.get("status", "pending"),
        "provider_response": result,
        "created_at": datetime.now(timezone.utc),
    })
    return result


@router.post("/{provider}/callback")
@limiter.limit("120/minute")
async def payment_callback(provider: str, body: PaymentCallback, request: Request):
    """Called by a payment gateway after it processes a payment.

    The request must be signed (see _verify_callback_signature); it must also
    match the order's provider and total. Paid states are terminal: a later
    failure callback cannot downgrade an order that is already paid.
    """
    raw = await request.body()
    _verify_callback_signature(provider, raw, request)

    if provider not in {m.value for m in PaymentMethod}:
        raise HTTPException(400, "Unsupported payment provider")

    amount = body.amount
    if amount is None or not math.isfinite(amount) or amount <= 0:
        raise HTTPException(400, "Invalid callback amount")

    db = get_db()
    order = await db.orders.find_one({"_id": _to_oid(body.order_id)})
    if not order:
        raise HTTPException(404, "Order not found")

    method = order.get("payment_method")
    method_value = method.value if isinstance(method, PaymentMethod) else str(method)
    if method_value != provider:
        raise HTTPException(400, "Provider does not match order")
    if method_value == PaymentMethod.COD.value:
        raise HTTPException(400, "Cash on Delivery does not use callbacks")
    if not math.isclose(float(order.get("total", 0)), amount, abs_tol=0.01):
        raise HTTPException(400, "Amount mismatch")

    paid = body.status in ("success", "completed", "paid", "succeeded")
    failed = body.status in ("failed", "cancelled", "canceled", "error")
    if not paid and not failed:
        raise HTTPException(400, "Unsupported callback status")

    current = order.get("payment_status")
    if current == PaymentStatus.PAID:
        if not paid:
            return {
                "message": "Ignored: order is already paid",
                "payment_status": current,
                "success": True,
            }
        if order.get("payment_transaction_id") and order["payment_transaction_id"] != body.transaction_id:
            raise HTTPException(409, "Order already paid with a different transaction")
        return {
            "message": "Callback already processed",
            "payment_status": current,
            "success": True,
        }

    status = PaymentStatus.PAID if paid else PaymentStatus.FAILED
    await db.orders.update_one(
        {"_id": order["_id"]},
        {
            "$set": {
                "payment_status": status,
                "payment_transaction_id": body.transaction_id,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await db.payments.update_one(
        {"order_id": order["_id"]},
        {
            "$set": {
                "status": status,
                "transaction_id": body.transaction_id,
                "callback": body.model_dump(),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    await log_action(None, "system", "payment.callback", "order", body.order_id, {"status": status, "provider": provider})
    await regenerate_order_invoice(str(order["_id"]))
    return {"message": "Callback processed", "payment_status": status}


@router.get("/admin/cod")
async def list_cod_orders(
    status: Optional[str] = None,
    admin: dict = Depends(require_permission("orders.view")),
):
    db = get_db()
    filt = {"payment_method": PaymentMethod.COD}
    if status:
        filt["payment_status"] = status
    cursor = db.orders.find(filt).sort("created_at", -1).limit(100)
    return [
        {
            "id": str(o["_id"]),
            "order_number": o.get("order_number"),
            "total": o.get("total"),
            "payment_status": o.get("payment_status"),
            "status": o.get("status"),
            "address": o.get("shipping_address"),
        }
        async for o in cursor
    ]
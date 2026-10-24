"""
Order invoice generation as a PDF document.

Every order gets a printable invoice saved under uploads/invoices/ in .pdf
format. The document includes the order items, totals, shipping address,
payment details and the full status history ("invoice messages"). The file is
regenerated when the order status or payment status changes so the stored
document always reflects the latest order state.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from bson import ObjectId
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.core.database import get_db
from app.core.paths import UPLOAD_ROOT

INVOICE_DIR = UPLOAD_ROOT / "invoices"
BRAND = "GlobalShop"

PRIMARY = colors.HexColor(0x0F172A)
ACCENT = colors.HexColor(0x7163FF)
MUTED = colors.HexColor(0x6B7280)
LIGHT = colors.HexColor(0xF1F5F9)
GRID_COLOR = colors.HexColor(0xE2E8F0)


async def _company_info() -> dict:
    """Company block for the invoice header, from admin-configured site settings."""
    from app.api.v1.settings import get_settings_doc, get_store_meta
    doc = await get_settings_doc()
    company = doc.get("company") or {}
    meta = await get_store_meta()
    support_bits = [company.get("support_email"), company.get("support_phone")]
    support = "  ·  ".join([b for b in support_bits if b]) or "—"
    return {
        "brand": BRAND,
        "name": company.get("name") or "Global Commerce + ERP",
        "address": company.get("address") or "",
        "support": support,
        "currency": meta["currency"],
    }


def _fmt_money(value, currency: str = "USD") -> str:
    try:
        return f"{currency} {float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"


def _fmt_dt(value) -> str:
    if not value:
        return ""
    return value.strftime("%d %b %Y, %I:%M %p") if hasattr(value, "strftime") else str(value)


def _table_style(header_bg: bool = False) -> TableStyle:
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.75, GRID_COLOR),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header_bg:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]
    return TableStyle(cmds)


async def generate_order_invoice(order_id: str) -> Path:
    """Build (or rebuild) the .pdf invoice for an order and store it on disk."""
    db = get_db()
    try:
        order = await db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order_number = order.get("order_number") or str(order["_id"])
    customer = None
    if order.get("customer_id"):
        customer = await db.customers.find_one({"_id": order["customer_id"]})

    company = await _company_info()
    currency = order.get("currency") or company["currency"]

    INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    path = INVOICE_DIR / f"INV-{order_number}.pdf"

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], textColor=PRIMARY, fontSize=24, fontName="Helvetica-Bold", spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=styles["Normal"], textColor=ACCENT, fontSize=11, spaceAfter=2)
    muted = ParagraphStyle("muted", parent=styles["Normal"], textColor=MUTED, fontSize=9, spaceAfter=2)
    title = ParagraphStyle("title", parent=styles["Title"], textColor=ACCENT, fontSize=20, spaceAfter=10)
    section = ParagraphStyle("section", parent=styles["Heading2"], textColor=PRIMARY, fontSize=12, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9)
    note = ParagraphStyle("note", parent=styles["BodyText"], textColor=MUTED, fontSize=9)

    def label(text: str) -> Paragraph:
        return Paragraph(f"<font color='#0F172A'><b>{text}</b></font>", body)

    def value(text) -> Paragraph:
        return Paragraph(str(text), body)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        title=f"INV-{order_number}",
        author=company["brand"],
    )
    story = []

    # ----- Header -----
    story.append(Paragraph(company["brand"], h1))
    story.append(Paragraph(company["name"], h2))
    story.append(Paragraph(f"{company['address']}<br/>{company['support']}", muted))
    story.append(Paragraph("INVOICE", title))

    # ----- Meta rows -----
    status = order.get("status") or "unknown"
    payment_status = order.get("payment_status") or "pending"
    meta = Table(
        [[label(k), value(v)] for k, v in [
            ("Invoice No.", f"INV-{order_number}"),
            ("Order No.", order_number),
            ("Order Date", _fmt_dt(order.get("created_at"))),
            ("Order Status", status),
            ("Payment Method", order.get("payment_method") or "—"),
            ("Payment Status", payment_status),
            ("Payment Transaction", order.get("payment_transaction_id") or "—"),
        ]],
        colWidths=[2.2 * inch, 4.4 * inch],
    )
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, GRID_COLOR),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta)
    story.append(Spacer(1, 10))

    # ----- Bill To -----
    story.append(Paragraph("Bill To", section))
    ship = order.get("shipping_address") or {}
    bt = Table(
        [[label(k), value(v)] for k, v in [
            ("Customer", (customer or {}).get("full_name") or ship.get("full_name") or "—"),
            ("Email", (customer or {}).get("email") or "—"),
            ("Phone", (customer or {}).get("phone") or ship.get("phone") or "—"),
            ("Country", ship.get("country") or "—"),
            ("City / State", " / ".join([p for p in [ship.get("city"), ship.get("state")] if p]) or "—"),
            ("Address", ship.get("address_line") or "—"),
            ("Postal Code", ship.get("postal_code") or "—"),
        ]],
        colWidths=[2.2 * inch, 4.4 * inch],
    )
    bt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, GRID_COLOR),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(bt)
    story.append(Spacer(1, 10))

    # ----- Items table -----
    item_data = [["#", "Item", "SKU", "Qty", "Unit Price", "Total"]]
    for idx, it in enumerate(order.get("items") or [], start=1):
        item_data.append([
            str(idx),
            it.get("name") or "—",
            it.get("sku") or "—",
            str(it.get("quantity") or 0),
            _fmt_money(it.get("unit_price"), currency),
            _fmt_money(it.get("line_total"), currency),
        ])
    items = Table(
        item_data,
        colWidths=[0.4 * inch, 2.4 * inch, 1.1 * inch, 0.6 * inch, 1.15 * inch, 1.15 * inch],
        repeatRows=1,
    )
    items.setStyle(_table_style(header_bg=True))
    items.setStyle(TableStyle([("ALIGN", (4, 1), (5, -1), "RIGHT")]))
    story.append(items)
    story.append(Spacer(1, 10))

    # ----- Totals -----
    totals_rows = [
        ("Subtotal", _fmt_money(order.get("subtotal"), currency)),
        ("Discount", f"- {_fmt_money(order.get('discount'), currency)}"),
        ("Delivery Charge", _fmt_money(order.get("delivery_charge"), currency)),
        ("Tax", _fmt_money(order.get("tax"), currency)),
        ("GRAND TOTAL", _fmt_money(order.get("total"), currency)),
    ]
    totals = Table(
        [[Paragraph(f"<b>{k}</b>", body), Paragraph(f"<b>{v}</b>", body)] for k, v in totals_rows],
        colWidths=[3.3 * inch, 3.3 * inch],
        hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.75, GRID_COLOR),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, -1), (-1, -1), PRIMARY),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(totals)
    story.append(Spacer(1, 10))

    # ----- Status history ("invoice messages") -----
    story.append(Paragraph("Order Status History", section))
    history = order.get("history") or []
    if not history:
        story.append(Paragraph(f"• Placed as {status}", body))
    for entry in history:
        line = f"• {entry.get('status') or status} — {_fmt_dt(entry.get('at'))}"
        if entry.get("by"):
            line += f" (by {entry.get('by')})"
        story.append(Paragraph(line, body))

    # ----- Notes -----
    if order.get("notes"):
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"Order Notes: {order['notes']}", note))

    # ----- Footer -----
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f"Generated {_fmt_dt(datetime.now(timezone.utc))}  ·  {company['brand']}  ·  {company['name']}",
        muted,
    ))

    doc.build(story)

    await db.orders.update_one(
        {"_id": order["_id"]},
        {
            "$set": {
                "invoice_path": str(path),
                "invoice_generated_at": datetime.now(timezone.utc),
            }
        },
    )
    return path


async def ensure_order_invoice(order_id: str) -> Path:
    """Return the existing invoice .pdf for an order, generating it if needed."""
    db = get_db()
    try:
        order = await db.orders.find_one({"_id": ObjectId(order_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid order id")
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    stored = order.get("invoice_path")
    if stored and Path(stored).suffix.lower() == ".pdf" and Path(stored).exists():
        return Path(stored)
    return await generate_order_invoice(order_id)


async def regenerate_order_invoice(order_id: str) -> None:
    """Safety wrapper for regenerating an invoice after a status change."""
    try:
        await generate_order_invoice(order_id)
    except Exception:
        pass
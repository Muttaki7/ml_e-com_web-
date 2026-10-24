"""Transactional email with no third-party SDK: plain SMTP, optional."""
import asyncio
from email.message import EmailMessage
from email.utils import formataddr
from html import escape
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def _format_money(amount: float, currency: str) -> str:
    return f"{currency} {amount:,.2f}"


def _send(message: EmailMessage) -> None:
    import smtplib

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    timeout = 20
    if settings.SMTP_SSL:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.ehlo()
        if settings.SMTP_STARTTLS:
            smtp.starttls()
            smtp.ehlo()
        if settings.SMTP_USER:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(message)


async def _deliver(to: str, subject: str, text: str, html: str) -> bool:
    if not settings.SMTP_HOST:
        return False
    sender = settings.SMTP_FROM or settings.SMTP_USER
    if not sender:
        logger.warning("email.skipped", reason="SMTP_FROM or SMTP_USER is required")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.APP_NAME, sender))
    message["To"] = to
    if settings.SUPPORT_EMAIL:
        message["Reply-To"] = settings.SUPPORT_EMAIL
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        await asyncio.to_thread(_send, message)
        logger.info("email.sent", to=to, subject=subject)
        return True
    except Exception as exc:
        # Never fail an order because a notification could not be delivered.
        logger.error("email.failed", to=to, error=str(exc)[:200])
        return False


async def send_order_confirmation(customer: dict, order: dict) -> bool:
    to = (customer.get("email") or "").strip()
    if not to:
        return False

    currency = order.get("currency") or settings.CURRENCY
    rows = []
    text_lines = []
    for item in order.get("items", []):
        line = item.get("line_total", 0)
        rows.append(
            "<tr>"
            f"<td style='padding:6px 0'>{escape(str(item.get('name', '')))}</td>"
            f"<td style='padding:6px 0;text-align:center'>{int(item.get('quantity', 0))}</td>"
            f"<td style='padding:6px 0;text-align:right'>{escape(_format_money(line, currency))}</td>"
            "</tr>"
        )
        text_lines.append(
            f"- {item.get('name')} x{int(item.get('quantity', 0))}: {_format_money(line, currency)}"
        )

    order_number = order.get("order_number", "")
    name = escape((customer.get("full_name") or "there").split(" ")[0])
    total = _format_money(order.get("total", 0), currency)
    method = order.get("payment_method")
    method_value = method.value if hasattr(method, "value") else str(method)

    text = (
        f"Hi {customer.get('full_name') or 'there'},\n\n"
        f"We received your order {order_number}.\n\n"
        + "\n".join(text_lines)
        + f"\n\nDelivery: {_format_money(order.get('delivery_charge', 0), currency)}"
        f"\nTotal: {total}\nPayment: {method_value.upper()}\n\n"
        "We will contact you when the order is on its way.\n\n"
        f"{settings.APP_NAME}"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;color:#0f172a;max-width:560px;margin:auto">
      <h2 style="margin:0 0 8px">Order received</h2>
      <p style="margin:0 0 16px">Hi {name}, thanks for shopping with us.</p>
      <p style="margin:0 0 16px">Order <strong>#{escape(order_number)}</strong></p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <thead><tr style="border-bottom:1px solid #e2e8f0;text-align:left">
          <th style="padding:8px 0">Item</th><th style="text-align:center">Qty</th>
          <th style="text-align:right">Total</th>
        </tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <p style="margin:16px 0 0">Delivery: {escape(_format_money(order.get('delivery_charge', 0), currency))}</p>
      <p style="margin:4px 0 0;font-size:18px"><strong>Total: {escape(total)}</strong></p>
      <p style="margin:8px 0 0;color:#475569">Payment: {escape(method_value.upper())}</p>
      <p style="margin:24px 0 0;color:#64748b;font-size:12px">{escape(settings.APP_NAME)}</p>
    </div>
    """

    return await _deliver(to, f"Order {order_number} received", text, html)


async def send_test_email(to: str) -> bool:
    return await _deliver(
        to,
        "SMTP configuration test",
        "Your store's SMTP settings are working.",
        "<p>Your store's SMTP settings are working.</p>",
    )

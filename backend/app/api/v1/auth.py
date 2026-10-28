from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from app.schemas.auth import (
    CustomerRegister, CustomerLogin, AdminLogin, TwoFAVerify,
    TwoFASetupConfirm, TwoFADisable, TokenResponse,
    RefreshRequest, MessageResponse,
)
from app.services import auth_service
from app.services.admin_service import get_admin
from app.api.deps import get_current_admin, get_current_customer, get_client_ip
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------- Public demo ----------
@router.get("/demo")
@limiter.limit("20/minute")
async def demo_accounts(request: Request):
    """Credentials for the one-click demo buttons.

    Returns 404 unless DEMO_MODE is explicitly enabled. The accounts are
    created by `python -m app.cli.bootstrap` on the same demo deployment.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "enabled": True,
        "admin": {
            "email": settings.DEMO_ADMIN_EMAIL,
            "password": settings.DEMO_ADMIN_PASSWORD,
        },
        "customer": {
            "email": settings.DEMO_CUSTOMER_EMAIL,
            "password": settings.DEMO_CUSTOMER_PASSWORD,
        },
    }


# ---------- Admin profile ----------
@router.get("/admin/me")
async def admin_me(admin: dict = Depends(get_current_admin)):
    """Return the authenticated admin's profile. Only admin tokens pass here."""
    return await get_admin(admin["id"])


# ---------- Customer ----------
@router.post("/customer/register", response_model=dict)
@limiter.limit("5/minute")
async def customer_register(body: CustomerRegister, request: Request):
    ip = get_client_ip(request)
    user = await auth_service.register_customer(body.model_dump(), ip=ip)
    return {"message": "Registered successfully", "user": user}


@router.post("/customer/login")
@limiter.limit("10/minute")
async def customer_login(body: CustomerLogin, request: Request):
    """Returns full tokens, or a 2FA challenge when the customer has 2FA enabled."""
    ip = get_client_ip(request)
    return await auth_service.login_customer(body.email, body.password, ip=ip)


@router.post("/customer/2fa/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
async def customer_2fa_verify(body: TwoFAVerify, request: Request):
    ip = get_client_ip(request)
    return await auth_service.verify_customer_2fa(body.temp_token, body.code, ip=ip)


@router.post("/customer/2fa/setup")
@limiter.limit("10/minute")
async def customer_2fa_setup(request: Request, customer: dict = Depends(get_current_customer)):
    """Start enrolling TOTP 2FA: returns secret + QR + one-time backup codes."""
    return await auth_service.setup_customer_2fa(customer["id"])


@router.post("/customer/2fa/confirm", response_model=MessageResponse)
@limiter.limit("10/minute")
async def customer_2fa_confirm(
    body: TwoFASetupConfirm,
    request: Request,
    customer: dict = Depends(get_current_customer),
):
    return await auth_service.confirm_customer_2fa(customer["id"], body.code)


@router.post("/customer/2fa/disable", response_model=MessageResponse)
@limiter.limit("10/minute")
async def customer_2fa_disable(
    body: TwoFADisable,
    request: Request,
    customer: dict = Depends(get_current_customer),
):
    ip = get_client_ip(request)
    return await auth_service.disable_customer_2fa(customer["id"], body.code, ip=ip)


@router.post("/customer/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def customer_refresh(body: RefreshRequest, request: Request):
    return await auth_service.refresh_tokens(body.refresh_token)


@router.post("/customer/logout", response_model=MessageResponse)
@limiter.limit("30/minute")
async def customer_logout(request: Request, body: Optional[RefreshRequest] = None):
    if body and body.refresh_token:
        await auth_service.revoke_refresh_token(body.refresh_token)
    return {"message": "Logged out", "success": True}


# ---------- Admin ----------
@router.post("/admin/login")
@limiter.limit("10/minute")
async def admin_login(body: AdminLogin, request: Request):
    """
    Step 1: validate password. Returns a 2FA challenge (temp_token) when 2FA
    is enabled, otherwise full tokens.
    """
    ip = get_client_ip(request)
    return await auth_service.login_admin_password(body.email, body.password, ip=ip)


@router.post("/admin/2fa/verify", response_model=TokenResponse)
@limiter.limit("10/minute")
async def admin_2fa_verify(body: TwoFAVerify, request: Request):
    """Step 2: exchange the challenge temp_token + TOTP/backup code for tokens."""
    ip = get_client_ip(request)
    return await auth_service.verify_admin_2fa(body.temp_token, body.code, ip=ip)


@router.post("/admin/2fa/setup")
@limiter.limit("10/minute")
async def admin_2fa_setup(request: Request, admin: dict = Depends(get_current_admin)):
    return await auth_service.setup_admin_2fa(admin["id"])


@router.post("/admin/2fa/confirm", response_model=MessageResponse)
@limiter.limit("10/minute")
async def admin_2fa_confirm(
    body: TwoFASetupConfirm,
    request: Request,
    admin: dict = Depends(get_current_admin),
):
    return await auth_service.confirm_admin_2fa(admin["id"], body.code)


@router.post("/admin/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
async def admin_refresh(body: RefreshRequest, request: Request):
    return await auth_service.refresh_tokens(body.refresh_token)


@router.post("/admin/logout", response_model=MessageResponse)
@limiter.limit("30/minute")
async def admin_logout(request: Request, body: Optional[RefreshRequest] = None):
    if body and body.refresh_token:
        await auth_service.revoke_refresh_token(body.refresh_token)
    return {"message": "Logged out", "success": True}

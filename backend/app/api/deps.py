from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId

from app.core.security import decode_token
from app.core.database import get_db
from app.core.config import settings
from app.core.constants import resolve_admin_permissions

security = HTTPBearer(auto_error=False)


async def get_current_customer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "customer":
        raise HTTPException(status_code=401, detail="Invalid customer token")
    if payload.get("token_use") == "refresh":
        raise HTTPException(status_code=401, detail="Refresh token cannot be used as an access token")
    if payload.get("2fa_pending"):
        raise HTTPException(status_code=401, detail="2FA pending")
    db = get_db()
    user = await db.customers.find_one({"_id": ObjectId(payload["sub"])})
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Customer inactive")
    return {"id": str(user["_id"]), "email": user["email"], "full_name": user.get("full_name")}


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "admin":
        raise HTTPException(status_code=401, detail="Invalid admin token")
    if payload.get("token_use") == "refresh":
        raise HTTPException(status_code=401, detail="Refresh token cannot be used as an access token")
    if payload.get("2fa_pending"):
        raise HTTPException(status_code=401, detail="Complete 2FA first")
    db = get_db()
    admin = await db.admins.find_one({"_id": ObjectId(payload["sub"])})
    if not admin or admin.get("status") != "active":
        raise HTTPException(status_code=401, detail="Admin inactive")
    perms = resolve_admin_permissions(
        admin.get("role"),
        admin.get("is_main_admin", False),
        admin.get("permissions"),
    )
    return {
        "id": str(admin["_id"]),
        "email": admin["email"],
        "role": admin.get("role"),
        "permissions": perms,
        "is_main_admin": admin.get("is_main_admin", False),
        "full_name": admin.get("full_name") or admin.get("name"),
    }


def require_permission(*required: str):
    """Dependency factory: admin must have at least one of the listed permissions (or be Main Admin)."""
    async def checker(admin: dict = Depends(get_current_admin)) -> dict:
        if admin.get("is_main_admin"):
            return admin
        admin_perms = set(admin.get("permissions") or [])
        if not any(p in admin_perms for p in required):
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission. Required one of: {', '.join(required)}",
            )
        return admin
    return checker


def get_client_ip(request: Request) -> str:
    # X-Forwarded-For is client-controlled unless a trusted proxy rewrites it.
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
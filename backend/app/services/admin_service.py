import asyncio
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db
from app.core.security import hash_password
from app.core.constants import ROLE_PERMISSIONS, AdminRole
from app.services.audit_service import log_action
from app.services.auth_service import _serialize_admin


async def create_admin(data: dict, creator_id: str, creator_is_main: bool) -> dict:
    db = get_db()
    if await db.admins.find_one({"email": data["email"].lower()}):
        raise HTTPException(status_code=400, detail="Email already exists")

    role = data["role"]
    if role == AdminRole.MAIN_ADMIN and not creator_is_main:
        raise HTTPException(status_code=403, detail="Only Main Admin can create another Main Admin")

    # Never allow non-main to create main
    is_main = role == AdminRole.MAIN_ADMIN and creator_is_main

    perms = data.get("permissions")
    if perms is None:
        perms = ROLE_PERMISSIONS.get(role, [])

    doc = {
        "full_name": data["full_name"],
        "email": data["email"].lower(),
        "phone": data.get("phone"),
        "password_hash": await asyncio.to_thread(hash_password, data["temporary_password"]),
        "role": role,
        "permissions": perms,
        "two_factor_required": data.get("two_factor_required", True),
        "two_factor": None,
        "is_main_admin": is_main,
        "status": data.get("status", "active"),
        "failed_login_attempts": 0,
        "lockout_until": None,
        "must_change_password": True,
        "created_by": creator_id,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.admins.insert_one(doc)
    admin_id = str(result.inserted_id)
    await log_action(
        creator_id, "admin", "admin.created", "admin", admin_id,
        details={"role": role, "permissions": perms, "email": data["email"]},
    )
    return await get_admin(admin_id)


async def get_admin(admin_id: str) -> dict:
    db = get_db()
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return _serialize_admin(admin)


async def list_admins(skip: int = 0, limit: int = 50) -> List[dict]:
    db = get_db()
    cursor = db.admins.find().skip(skip).limit(limit).sort("created_at", -1)
    return [_serialize_admin(a) async for a in cursor]


async def update_admin(admin_id: str, data: dict, actor_id: str, actor_is_main: bool) -> dict:
    db = get_db()
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    # Protect Main Admin
    if admin.get("is_main_admin") and not actor_is_main:
        raise HTTPException(status_code=403, detail="Cannot modify Main Admin")

    # Prevent self-privilege escalation
    if admin_id == actor_id:
        if "role" in data or "permissions" in data:
            raise HTTPException(status_code=403, detail="Cannot change your own role or permissions")

    if data.get("role") == AdminRole.MAIN_ADMIN and not actor_is_main:
        raise HTTPException(status_code=403, detail="Only Main Admin can assign Main Admin role")

    update = {k: v for k, v in data.items() if v is not None}
    if "role" in update and "permissions" not in update:
        update["permissions"] = ROLE_PERMISSIONS.get(update["role"], [])
    if update.get("role") == AdminRole.MAIN_ADMIN:
        update["is_main_admin"] = True
        update["permissions"] = ROLE_PERMISSIONS[AdminRole.MAIN_ADMIN]

    update["updated_at"] = datetime.now(timezone.utc)
    await db.admins.update_one({"_id": ObjectId(admin_id)}, {"$set": update})
    await log_action(actor_id, "admin", "admin.updated", "admin", admin_id, details=update)
    return await get_admin(admin_id)


async def disable_admin(admin_id: str, actor_id: str, actor_is_main: bool) -> dict:
    db = get_db()
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if admin.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Cannot disable Main Admin")
    if admin_id == actor_id:
        raise HTTPException(status_code=403, detail="Cannot disable yourself")

    await db.admins.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"status": "disabled", "updated_at": datetime.now(timezone.utc)}},
    )
    await log_action(actor_id, "admin", "admin.disabled", "admin", admin_id)
    return {"message": "Admin disabled", "success": True}


async def reset_admin_2fa(admin_id: str, actor_id: str, actor_is_main: bool) -> dict:
    db = get_db()
    admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if admin.get("is_main_admin") and not actor_is_main:
        raise HTTPException(status_code=403, detail="Cannot reset Main Admin 2FA")

    await db.admins.update_one(
        {"_id": ObjectId(admin_id)},
        {"$set": {"two_factor": None, "updated_at": datetime.now(timezone.utc)}},
    )
    await log_action(actor_id, "admin", "admin.2fa_reset", "admin", admin_id)
    return {"message": "2FA reset. Admin must re-enroll on next login.", "success": True}
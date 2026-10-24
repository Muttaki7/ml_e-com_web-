import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_totp_secret, get_totp_uri, generate_qr_base64,
    verify_totp, generate_backup_codes, hash_backup_code, verify_backup_code,
)
from app.core.config import settings
from app.core.constants import UserStatus, resolve_admin_permissions
from app.services.audit_service import log_action

TWOFA_CHALLENGE_MINUTES = 5

# Verified against when the account does not exist, so a missing account and a
# wrong password take comparable time (prevents login user enumeration).
DUMMY_PASSWORD_HASH = "$2b$12$ZEqspr6we4AeMwUXaoWbbuWuOXXRK73GCIGy1XRIQDkA42FvHmHAq"


# ---------- Customer Auth ----------
async def register_customer(data: dict, ip: str = None) -> dict:
    db = get_db()
    existing = await db.customers.find_one({"email": data["email"].lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    doc = {
        "full_name": data["full_name"],
        "email": data["email"].lower(),
        "phone": data["phone"],
        "password_hash": await asyncio.to_thread(hash_password, data["password"]),
        "status": UserStatus.ACTIVE,
        "addresses": [],
        "two_factor": None,
        "pending_2fa": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.customers.insert_one(doc)
    customer_id = str(result.inserted_id)
    await log_action(customer_id, "customer", "customer.register", "customer", customer_id, ip=ip)
    return await get_customer_safe(customer_id)


async def login_customer(email: str, password: str, ip: str = None) -> dict:
    db = get_db()
    user = await db.customers.find_one({"email": email.lower()})
    now = datetime.now(timezone.utc)

    if user and user.get("lockout_until") and user["lockout_until"] > now:
        raise HTTPException(status_code=423, detail="Account temporarily locked. Try again later.")

    if user:
        valid = await asyncio.to_thread(verify_password, password, user["password_hash"])
    else:
        await asyncio.to_thread(verify_password, password, DUMMY_PASSWORD_HASH)
        valid = False

    if not valid:
        if user:
            fails = user.get("failed_login_attempts", 0) + 1
            update = {"failed_login_attempts": fails}
            if fails >= settings.MAX_LOGIN_ATTEMPTS:
                update["lockout_until"] = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
            await db.customers.update_one({"_id": user["_id"]}, {"$set": update})
        await log_action(None, "customer", "customer.login_failed", details={"email": email}, ip=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("status") != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="Account disabled")

    await db.customers.update_one(
        {"_id": user["_id"]},
        {"$set": {"failed_login_attempts": 0, "lockout_until": None}},
    )

    if (user.get("two_factor") or {}).get("enabled"):
        return await begin_2fa_challenge(user, "customer")

    return await _issue_customer_tokens(user, ip)


async def verify_customer_2fa(temp_token: str, code: str, ip: str = None) -> dict:
    db = get_db()
    user = await _validate_2fa_challenge(temp_token, "customer")
    kind = await _check_2fa_code(user, code)
    if kind is None:
        fails = await _record_2fa_failure(db.customers, user)
        await log_action(str(user["_id"]), "customer", "customer.2fa_failed", ip=ip)
        if fails >= settings.MAX_2FA_ATTEMPTS:
            raise HTTPException(status_code=423, detail="Too many attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    if kind == "backup":
        await _burn_backup_code(db.customers, user, code)

    await db.customers.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "pending_2fa": None,
            "two_factor_failed_attempts": 0,
            "two_factor_locked_until": None,
        }},
    )
    await log_action(str(user["_id"]), "customer", "customer.2fa_success", ip=ip)
    return await _issue_customer_tokens(user, ip)


async def _issue_customer_tokens(user: dict, ip: str = None) -> dict:
    access = create_access_token(str(user["_id"]), "customer")
    refresh = create_refresh_token(str(user["_id"]), "customer")
    await _store_refresh(str(user["_id"]), "customer", refresh)
    await log_action(str(user["_id"]), "customer", "customer.login", ip=ip)

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _serialize_customer(user),
    }


# ---------- Admin Auth ----------
async def login_admin_password(email: str, password: str, ip: str = None) -> dict:
    """Step 1: validate password. If 2FA required, return a bound challenge."""
    db = get_db()
    admin = await db.admins.find_one({"email": email.lower()})
    if not admin:
        await asyncio.to_thread(verify_password, password, DUMMY_PASSWORD_HASH)
        await log_action(None, "admin", "admin.login_failed", details={"email": email}, ip=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Lockout check
    if admin.get("lockout_until") and admin["lockout_until"] > datetime.now(timezone.utc):
        raise HTTPException(status_code=423, detail="Account temporarily locked. Try again later.")

    if not await asyncio.to_thread(verify_password, password, admin["password_hash"]):
        fails = admin.get("failed_login_attempts", 0) + 1
        update = {"failed_login_attempts": fails}
        if fails >= settings.MAX_LOGIN_ATTEMPTS:
            update["lockout_until"] = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_MINUTES)
        await db.admins.update_one({"_id": admin["_id"]}, {"$set": update})
        await log_action(str(admin["_id"]), "admin", "admin.login_failed", ip=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Reset failed attempts
    await db.admins.update_one(
        {"_id": admin["_id"]},
        {"$set": {"failed_login_attempts": 0, "lockout_until": None}},
    )

    if admin.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account disabled")

    if admin.get("two_factor_required", True) and (admin.get("two_factor") or {}).get("enabled"):
        return await begin_2fa_challenge(admin, "admin")

    # 2FA not enforced/enrolled yet → issue full tokens (enrollment is forced via /admin/2fa/setup)
    return await _issue_admin_tokens(admin, ip)


async def verify_admin_2fa(temp_token: str, code: str, ip: str = None) -> dict:
    db = get_db()
    admin = await _validate_2fa_challenge(temp_token, "admin")
    kind = await _check_2fa_code(admin, code)
    if kind is None:
        fails = await _record_2fa_failure(db.admins, admin)
        await log_action(str(admin["_id"]), "admin", "admin.2fa_failed", ip=ip)
        if fails >= settings.MAX_2FA_ATTEMPTS:
            raise HTTPException(status_code=423, detail="Too many attempts. Try again later.")
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    if kind == "backup":
        await _burn_backup_code(db.admins, admin, code)

    await db.admins.update_one(
        {"_id": admin["_id"]},
        {"$set": {
            "pending_2fa": None,
            "two_factor_failed_attempts": 0,
            "two_factor_locked_until": None,
        }},
    )
    await log_action(str(admin["_id"]), "admin", "admin.2fa_success", ip=ip)
    return await _issue_admin_tokens(admin, ip)


# ---------- 2FA challenge lifecycle ----------
async def begin_2fa_challenge(user: dict, token_type: str) -> dict:
    db = get_db()
    collection = db.admins if token_type == "admin" else db.customers

    # Account-level lock: restarting login must not reset the 2FA attempt budget.
    locked_until = user.get("two_factor_locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=423, detail="Too many 2FA attempts. Try again later.")

    temp = create_access_token(
        str(user["_id"]),
        token_type,
        extra={"2fa_pending": True},
        expires_minutes=TWOFA_CHALLENGE_MINUTES,
    )
    payload = decode_token(temp)
    await collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "pending_2fa": {
                "jti": payload["jti"],
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=TWOFA_CHALLENGE_MINUTES),
            }
        }},
    )
    return {
        "requires_2fa": True,
        "message": "Two-factor authentication required",
        "temp_token": temp,
    }


async def _validate_2fa_challenge(temp_token: str, token_type: str) -> dict:
    """Resolve a 2FA temp token to its account, enforcing binding and expiry."""
    payload = decode_token(temp_token)
    if not payload or payload.get("type") != token_type or not payload.get("2fa_pending"):
        raise HTTPException(status_code=401, detail="Invalid 2FA challenge")

    db = get_db()
    collection = db.admins if token_type == "admin" else db.customers
    user = await collection.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid 2FA challenge")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account disabled")

    pending = user.get("pending_2fa") or {}
    if pending.get("jti") != payload.get("jti"):
        raise HTTPException(status_code=401, detail="2FA challenge expired. Start login again.")
    if pending.get("expires_at") and pending["expires_at"] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="2FA challenge expired. Start login again.")

    locked_until = user.get("two_factor_locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=423, detail="Too many attempts. Try again later.")

    return user


async def _check_2fa_code(user: dict, code: str) -> Optional[str]:
    """Return "totp" or "backup" when the code is accepted, else None.

    A 6-digit TOTP is checked first; if it fails, the code is tried against
    the account's hashed backup codes (8-char). Callers burn backup codes
    via _burn_backup_code when "backup" is returned.
    """
    two_factor = user.get("two_factor") or {}
    secret = two_factor.get("secret")
    if not secret:
        return None
    code = (code or "").strip().replace(" ", "")
    if len(code) == settings.TOTP_DIGITS and code.isdigit():
        # A TOTP-shaped code never matches an 8-char backup code; skip the
        # expensive bcrypt loop so bad 6-digit codes stay cheap to reject.
        return "totp" if verify_totp(secret, code) else None
    for hashed in two_factor.get("backup_codes") or []:
        if await asyncio.to_thread(verify_backup_code, code, hashed):
            return "backup"
    return None


async def _burn_backup_code(collection, user: dict, code: str) -> None:
    """Remove the one backup code that matched (single-use)."""
    two_factor = user.get("two_factor") or {}
    codes = list(two_factor.get("backup_codes") or [])
    remaining = []
    burned = False
    for hashed in codes:
        if not burned and await asyncio.to_thread(verify_backup_code, code, hashed):
            burned = True
            continue
        remaining.append(hashed)
    if burned:
        await collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"two_factor.backup_codes": remaining}},
        )


async def _record_2fa_failure(collection, user: dict) -> int:
    """Count a bad code on the account, not the challenge (cannot be reset by
    starting a new login)."""
    fails = int(user.get("two_factor_failed_attempts") or 0) + 1
    update = {"two_factor_failed_attempts": fails}
    if fails >= settings.MAX_2FA_ATTEMPTS:
        update["two_factor_locked_until"] = datetime.now(timezone.utc) + timedelta(
            minutes=settings.LOCKOUT_MINUTES
        )
    await collection.update_one({"_id": user["_id"]}, {"$set": update})
    return fails


# ---------- 2FA enrollment (admins & customers share the same flow) ----------
async def _setup_2fa(collection, user_id: str) -> dict:
    user = await collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    secret = generate_totp_secret()
    uri = get_totp_uri(secret, user["email"])
    qr = await asyncio.to_thread(generate_qr_base64, uri)
    backup = generate_backup_codes()
    backup_hashes = await asyncio.to_thread(
        lambda: [hash_backup_code(c) for c in backup]
    )

    await collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "two_factor": {
                "secret": secret,
                "enabled": False,
                "backup_codes": backup_hashes,
                "pending": True,
            },
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    return {
        "secret": secret,
        "qr_code_base64": qr,
        "otpauth_uri": uri,
        "backup_codes": backup,  # shown once
        "message": "Scan the QR with an authenticator app, then confirm with a code",
    }


async def _confirm_2fa(collection, user_id: str, code: str, audit_actor: str, audit_type: str, audit_ip: str = None) -> dict:
    user = await collection.find_one({"_id": ObjectId(user_id)})
    if not user or not (user.get("two_factor") or {}).get("secret"):
        raise HTTPException(status_code=400, detail="No pending 2FA setup")

    if not verify_totp(user["two_factor"]["secret"], code):
        raise HTTPException(status_code=400, detail="Invalid code")

    await collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "two_factor.enabled": True,
            "two_factor.pending": False,
            "two_factor_failed_attempts": 0,
            "two_factor_locked_until": None,
            "pending_2fa": None,
        }},
    )
    await log_action(audit_actor, audit_type, f"{audit_type}.2fa_enrolled", ip=audit_ip)
    return {"message": "2FA enabled successfully", "success": True}


async def _disable_2fa(collection, user_id: str, code: str, audit_actor: str, audit_type: str, audit_ip: str = None) -> dict:
    user = await collection.find_one({"_id": ObjectId(user_id)})
    two_factor = (user or {}).get("two_factor") or {}
    if not two_factor.get("enabled"):
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    kind = await _check_2fa_code(user, code)
    if kind is None:
        raise HTTPException(status_code=400, detail="Invalid code")

    await collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "two_factor": None,
            "pending_2fa": None,
            "two_factor_failed_attempts": 0,
            "two_factor_locked_until": None,
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    await log_action(audit_actor, audit_type, f"{audit_type}.2fa_disabled", ip=audit_ip)
    return {"message": "2FA disabled", "success": True}


# Admin enrollment wrappers
async def setup_admin_2fa(admin_id: str) -> dict:
    db = get_db()
    return await _setup_2fa(db.admins, admin_id)


async def confirm_admin_2fa(admin_id: str, code: str) -> dict:
    db = get_db()
    return await _confirm_2fa(db.admins, admin_id, code, admin_id, "admin")


# Customer enrollment
async def setup_customer_2fa(customer_id: str) -> dict:
    db = get_db()
    return await _setup_2fa(db.customers, customer_id)


async def confirm_customer_2fa(customer_id: str, code: str, ip: str = None) -> dict:
    db = get_db()
    return await _confirm_2fa(db.customers, customer_id, code, customer_id, "customer", audit_ip=ip)


async def disable_customer_2fa(customer_id: str, code: str, ip: str = None) -> dict:
    db = get_db()
    return await _disable_2fa(db.customers, customer_id, code, customer_id, "customer", audit_ip=ip)


async def _issue_admin_tokens(admin: dict, ip: str = None) -> dict:
    perms = resolve_admin_permissions(
        admin.get("role"),
        admin.get("is_main_admin", False),
        admin.get("permissions"),
    )

    access = create_access_token(
        str(admin["_id"]),
        "admin",
        extra={
            "role": admin.get("role"),
            "permissions": perms,
            "is_main_admin": admin.get("is_main_admin", False),
        },
    )
    refresh = create_refresh_token(str(admin["_id"]), "admin")
    await _store_refresh(str(admin["_id"]), "admin", refresh)
    await log_action(str(admin["_id"]), "admin", "admin.login", ip=ip)

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": _serialize_admin(admin),
    }


async def _store_refresh(user_id: str, token_type: str, token: str) -> None:
    db = get_db()
    payload = decode_token(token)
    if not payload:
        return
    await db.refresh_tokens.insert_one({
        "user_id": user_id,
        "token_type": token_type,
        "token_jti": payload["jti"],
        "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        "created_at": datetime.now(timezone.utc),
    })


async def refresh_tokens(refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if not payload or payload.get("token_use") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    db = get_db()
    stored = await db.refresh_tokens.find_one({"token_jti": payload["jti"]})
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")

    token_type = payload["type"]
    user_id = payload["sub"]

    if token_type == "admin":
        admin = await db.admins.find_one({"_id": ObjectId(user_id)})
        if not admin or admin.get("status") != "active":
            raise HTTPException(status_code=401, detail="Admin inactive")
        # revoke old
        await db.refresh_tokens.delete_one({"token_jti": payload["jti"]})
        return await _issue_admin_tokens(admin)
    else:
        user = await db.customers.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("status") != UserStatus.ACTIVE:
            raise HTTPException(status_code=401, detail="User inactive")
        await db.refresh_tokens.delete_one({"token_jti": payload["jti"]})
        access = create_access_token(user_id, "customer")
        new_refresh = create_refresh_token(user_id, "customer")
        await _store_refresh(user_id, "customer", new_refresh)
        return {
            "access_token": access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": _serialize_customer(user),
        }


async def revoke_refresh_token(refresh_token: str) -> None:
    """Delete a refresh token from the allow-list (logout)."""
    payload = decode_token(refresh_token)
    if payload and payload.get("token_use") == "refresh" and payload.get("jti"):
        db = get_db()
        await db.refresh_tokens.delete_one({"token_jti": payload["jti"]})


def _serialize_customer(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "full_name": user.get("full_name"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "status": user.get("status"),
        "two_factor_enabled": bool((user.get("two_factor") or {}).get("enabled")),
    }


def _serialize_admin(admin: dict) -> dict:
    two_factor = admin.get("two_factor") or {}
    perms = resolve_admin_permissions(
        admin.get("role"),
        admin.get("is_main_admin", False),
        admin.get("permissions"),
    )
    return {
        "id": str(admin["_id"]),
        "full_name": admin.get("full_name") or admin.get("name"),
        "email": admin.get("email"),
        "phone": admin.get("phone"),
        "role": admin.get("role"),
        "permissions": perms,
        "is_main_admin": admin.get("is_main_admin", False),
        "two_factor_enabled": bool(two_factor.get("enabled")),
        "two_factor_required": admin.get("two_factor_required", True),
        "status": admin.get("status"),
    }


async def get_customer_safe(customer_id: str) -> dict:
    db = get_db()
    user = await db.customers.find_one({"_id": ObjectId(customer_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize_customer(user)

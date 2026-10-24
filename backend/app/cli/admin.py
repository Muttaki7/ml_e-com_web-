"""Production admin management CLI.

Run from backend/ (or inside the backend container):
    python -m app.cli.admin create --email owner@example.com --name "Store Owner" --enroll-2fa
    python -m app.cli.admin enroll-2fa --email owner@example.com
    python -m app.cli.admin reset-password --email owner@example.com
    python -m app.cli.admin list
"""
import argparse
import asyncio
import getpass
import sys
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from app.core.config import settings
from app.core.constants import AdminRole, ROLE_PERMISSIONS
from app.core.database import close_db, connect_db, get_db
from app.core.security import hash_password
from app.services import auth_service


def _prompt_password(confirm: bool = True) -> str:
    password = getpass.getpass("Password (min 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters")
    if confirm and getpass.getpass("Repeat password: ") != password:
        raise SystemExit("Passwords do not match")
    return password


def _print_qr(uri: str) -> None:
    try:
        import qrcode

        code = qrcode.QRCode(border=1)
        code.add_data(uri)
        code.print_ascii(invert=True)
    except Exception:
        print("Open this URI in your authenticator app:")
        print(uri)


async def _find_admin(email: str) -> Optional[dict]:
    db = get_db()
    return await db.admins.find_one({"email": email.strip().lower()})


async def create_admin(email: str, name: str, password: Optional[str], enroll: bool) -> None:
    await connect_db()
    try:
        email = email.strip().lower()
        if await _find_admin(email):
            raise SystemExit(f"An admin with {email} already exists")
        password = password or _prompt_password()
        db = get_db()
        now = datetime.now(timezone.utc)
        result = await db.admins.insert_one({
            "full_name": name.strip() or "Store Owner",
            "email": email,
            "phone": "",
            "password_hash": hash_password(password),
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
            "created_at": now,
            "updated_at": now,
        })
        print(f"Created Main Admin {email} (id={result.inserted_id})")
        if enroll:
            await _enroll(str(result.inserted_id), email)
        else:
            print("Enroll 2FA before exposing the site: python -m app.cli.admin enroll-2fa --email " + email)
    finally:
        await close_db()


async def _enroll(admin_id: str, email: str) -> None:
    setup = await auth_service.setup_admin_2fa(admin_id)
    print("\nScan this QR code with Google Authenticator / Authy / 1Password:\n")
    _print_qr(setup["otpauth_uri"])
    print("\nSecret (manual entry):", setup["secret"])
    print("\nBackup codes (shown once, store offline):")
    for code in setup["backup_codes"]:
        print("  ", code)
    if not sys.stdin.isatty():
        print("\nNon-interactive session: scan the QR, then run enroll-2fa again or confirm in the admin UI.")
        return
    code = input("\nEnter the 6-digit code to activate 2FA: ").strip()
    await auth_service.confirm_admin_2fa(admin_id, code)
    print("2FA activated. The account now requires a code at every login.")


async def enroll_2fa(email: str) -> None:
    await connect_db()
    try:
        admin = await _find_admin(email)
        if not admin:
            raise SystemExit(f"No admin found for {email}")
        if (admin.get("two_factor") or {}).get("enabled"):
            raise SystemExit("2FA is already enabled for this account")
        print(f"Enrolling 2FA for {admin['email']}")
        await _enroll(str(admin["_id"]), admin["email"])
    finally:
        await close_db()


async def reset_password(email: str) -> None:
    await connect_db()
    try:
        admin = await _find_admin(email)
        if not admin:
            raise SystemExit(f"No admin found for {email}")
        password = _prompt_password()
        await get_db().admins.update_one(
            {"_id": admin["_id"]},
            {"$set": {
                "password_hash": hash_password(password),
                "failed_login_attempts": 0,
                "lockout_until": None,
                "updated_at": datetime.now(timezone.utc),
            }},
        )
        print("Password updated. Existing refresh tokens remain valid until expiry; log out other sessions if needed.")
    finally:
        await close_db()


async def list_admins() -> None:
    await connect_db()
    try:
        async for admin in get_db().admins.find({}).sort("created_at", 1):
            enabled = bool((admin.get("two_factor") or {}).get("enabled"))
            print(
                f"{admin.get('email'):40} role={admin.get('role'):20} "
                f"status={admin.get('status'):8} 2fa={'yes' if enabled else 'NO'}"
            )
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage production administrators")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a Main Admin")
    create.add_argument("--email", required=True)
    create.add_argument("--name", default="Store Owner")
    create.add_argument("--password", help="Omit to be prompted securely")
    create.add_argument("--enroll-2fa", action="store_true")

    enroll = sub.add_parser("enroll-2fa", help="Enroll or finish enrolling TOTP 2FA")
    enroll.add_argument("--email", required=True)

    reset = sub.add_parser("reset-password", help="Set a new admin password")
    reset.add_argument("--email", required=True)

    sub.add_parser("list", help="List admins and 2FA status")

    args = parser.parse_args()
    if args.command == "create":
        asyncio.run(create_admin(args.email, args.name, args.password, args.enroll_2fa))
    elif args.command == "enroll-2fa":
        asyncio.run(enroll_2fa(args.email))
    elif args.command == "reset-password":
        asyncio.run(reset_password(args.email))
    else:
        asyncio.run(list_admins())


if __name__ == "__main__":
    main()

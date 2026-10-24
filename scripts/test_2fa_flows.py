"""In-memory DB stub + end-to-end 2FA flow tests (no MongoDB required)."""
import asyncio
import sys
import os
from copy import deepcopy
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from bson import ObjectId
import pyotp

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))


# ---------- minimal async in-memory collections ----------
def set_dotted(doc, path, value):
    parts = path.split(".")
    for p in parts[:-1]:
        doc = doc.setdefault(p, {})
    doc[parts[-1]] = value


def unset_dotted(doc, path):
    parts = path.split(".")
    for p in parts[:-1]:
        doc = doc.get(p, {})
    doc.pop(parts[-1], None)


class FakeCollection:
    def __init__(self):
        self.docs = {}

    async def find_one(self, filt):
        for d in self.docs.values():
            if all(self._match(d, k, v) for k, v in filt.items()):
                return d
        return None

    def _match(self, d, k, v):
        cur = d
        for p in k.split("."):
            if not isinstance(cur, dict):
                return False
            cur = cur.get(p)
        return cur == v

    async def update_one(self, filt, update, upsert=False):
        doc = await self.find_one(filt)
        if doc is None:
            if not upsert:
                return
            doc = {"_id": ObjectId()}
            self.docs[str(doc["_id"])] = doc
        for op, fields in update.items():
            for k, v in fields.items():
                if op == "$set":
                    set_dotted(doc, k, v)
                elif op == "$unset":
                    unset_dotted(doc, k)
        return doc

    async def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", ObjectId())
        self.docs[str(doc["_id"])] = doc
        return type("R", (), {"inserted_id": doc["_id"]})()

    async def delete_one(self, filt):
        for key, d in list(self.docs.items()):
            if all(self._match(d, k, v) for k, v in filt.items()):
                del self.docs[key]
                return


class FakeDB:
    def __init__(self):
        self.admins = FakeCollection()
        self.customers = FakeCollection()
        self.refresh_tokens = FakeCollection()
        self.audit_logs = FakeCollection()


async def main():
    import app.services.auth_service as auth_service
    import app.services.audit_service as audit_service
    from app.core.security import (
        hash_password, decode_token, generate_totp_secret,
        hash_backup_code, generate_backup_codes,
    )
    from app.schemas.auth import CustomerRegister
    from app.api.v1.orders import AddressIn

    fake = FakeDB()
    auth_service.get_db = lambda: fake
    audit_service.get_db = lambda: fake

    # ---------- fixtures ----------
    secret = generate_totp_secret()
    backup = generate_backup_codes()
    admin = {
        "_id": ObjectId(),
        "full_name": "Main Admin",
        "email": "admin@example.com",
        "password_hash": hash_password("Admin@12345"),
        "role": "main_admin",
        "is_main_admin": True,
        "status": "active",
        "two_factor_required": True,
        "two_factor": {
            "secret": secret,
            "enabled": True,
            "backup_codes": [hash_backup_code(c) for c in backup],
        },
        "failed_login_attempts": 0,
        "lockout_until": None,
        "pending_2fa": None,
    }
    fake.admins.docs[str(admin["_id"])] = admin

    # ---------- admin login -> challenge ----------
    ch = await auth_service.login_admin_password("admin@example.com", "Admin@12345")
    check("admin password step returns 2FA challenge", ch.get("requires_2fa") is True)
    temp = ch["temp_token"]
    payload = decode_token(temp)
    check("temp token carries 2fa_pending", payload.get("2fa_pending") is True)
    check("challenge has no email echo", "email" not in ch)

    # wrong password first
    try:
        await auth_service.login_admin_password("admin@example.com", "wrong")
        check("wrong password rejected", False)
    except Exception:
        check("wrong password rejected", True)

    # ---------- wrong codes -> lockout ----------
    ok_401 = False
    for _ in range(4):
        try:
            await auth_service.verify_admin_2fa(temp, "000000")
        except Exception as e:
            if getattr(e, "status_code", None) == 401:
                ok_401 = True
    check("four bad codes -> 401 each", ok_401)
    try:
        await auth_service.verify_admin_2fa(temp, "000000")
        check("fifth bad code -> 423 lockout", False)
    except Exception as e:
        check("fifth bad code -> 423 lockout", getattr(e, "status_code", None) == 423)

    # ---------- lockout cannot be bypassed by restarting login ----------
    try:
        await auth_service.login_admin_password("admin@example.com", "Admin@12345")
        check("re-login cannot bypass 2FA lockout", False)
    except Exception as e:
        check("re-login cannot bypass 2FA lockout", getattr(e, "status_code", None) == 423)

    # simulate expiry of the account-level 2FA lock
    admin["two_factor_locked_until"] = None
    admin["two_factor_failed_attempts"] = 0
    admin["pending_2fa"] = None

    # ---------- fresh challenge + valid TOTP ----------
    ch2 = await auth_service.login_admin_password("admin@example.com", "Admin@12345")
    totp = pyotp.TOTP(secret)
    tokens = await auth_service.verify_admin_2fa(ch2["temp_token"], totp.now())
    check("valid TOTP issues tokens", bool(tokens.get("access_token")))
    check("tokens carry admin type", decode_token(tokens["access_token"]).get("type") == "admin")
    check("tokens are not 2fa_pending", decode_token(tokens["access_token"]).get("2fa_pending") is None)
    check("successful 2FA resets failure counter", (admin.get("two_factor_failed_attempts") or 0) == 0)

    # ---------- single-use: replay same challenge ----------
    ch3 = await auth_service.login_admin_password("admin@example.com", "Admin@12345")
    await auth_service.verify_admin_2fa(ch3["temp_token"], totp.now())
    try:
        await auth_service.verify_admin_2fa(ch3["temp_token"], totp.now())
        check("replayed challenge rejected", False)
    except Exception:
        check("replayed challenge rejected", True)

    # ---------- garbage temp token ----------
    try:
        await auth_service.verify_admin_2fa("not.a.token", "123456")
        check("garbage temp token rejected", False)
    except Exception:
        check("garbage temp token rejected", True)

    # ---------- backup code single-use ----------
    ch4 = await auth_service.login_admin_password("admin@example.com", "Admin@12345")
    tokens4 = await auth_service.verify_admin_2fa(ch4["temp_token"], backup[0])
    check("backup code accepted", bool(tokens4.get("access_token")))
    ch5 = await auth_service.login_admin_password("admin@example.com", "Admin@12345")
    try:
        await auth_service.verify_admin_2fa(ch5["temp_token"], backup[0])
        check("used backup code burned", False)
    except Exception:
        check("used backup code burned", True)

    # ---------- cross-type token rejected (customer token on admin verify) ----------
    cust_secret = generate_totp_secret()
    customer = {
        "_id": ObjectId(),
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+14155552671",
        "password_hash": hash_password("Customer@123"),
        "status": "active",
        "two_factor": {"secret": cust_secret, "enabled": True, "backup_codes": []},
        "pending_2fa": None,
    }
    fake.customers.docs[str(customer["_id"])] = customer
    cch = await auth_service.login_customer("jane@example.com", "Customer@123")
    check("customer with 2FA gets challenge", cch.get("requires_2fa") is True)
    try:
        await auth_service.verify_admin_2fa(cch["temp_token"], pyotp.TOTP(cust_secret).now())
        check("customer token rejected on admin verify", False)
    except Exception:
        check("customer token rejected on admin verify", True)
    ctokens = await auth_service.verify_customer_2fa(cch["temp_token"], pyotp.TOTP(cust_secret).now())
    check("customer 2FA verify issues customer tokens", decode_token(ctokens["access_token"]).get("type") == "customer")

    # ---------- customer without 2FA logs in directly ----------
    customer["two_factor"]["enabled"] = False
    direct = await auth_service.login_customer("jane@example.com", "Customer@123")
    check("customer without 2FA gets tokens directly", bool(direct.get("access_token")) and "requires_2fa" not in direct)

    # ---------- customer 2FA enrollment ----------
    customer["two_factor"] = None
    setup = await auth_service.setup_customer_2fa(str(customer["_id"]))
    check("customer setup returns QR + backup codes", bool(setup.get("qr_code_base64")) and len(setup.get("backup_codes", [])) == 8)
    check("customer 2FA not enabled before confirm", customer["two_factor"]["enabled"] is False)
    try:
        await auth_service.confirm_customer_2fa(str(customer["_id"]), "000000")
        check("bad confirm code rejected", False)
    except Exception:
        check("bad confirm code rejected", True)
    await auth_service.confirm_customer_2fa(str(customer["_id"]), pyotp.TOTP(setup["secret"]).now())
    check("customer 2FA enabled after confirm", customer["two_factor"]["enabled"] is True)
    await auth_service.disable_customer_2fa(str(customer["_id"]), pyotp.TOTP(setup["secret"]).now())
    check("customer 2FA disabled", customer["two_factor"] is None)

    # ---------- phone validation ----------
    try:
        CustomerRegister(full_name="T T", email="t@t.com", phone="01712345678", password="Password1!")
        check("local BD-only phone rejected", False)
    except Exception:
        check("local BD-only phone rejected", True)
    u = CustomerRegister(full_name="T T", email="t@t.com", phone="+880 1712-345 678", password="Password1!")
    check("E164 phone accepted + normalized", u.phone == "+8801712345678")

    # ---------- address validation ----------
    a = AddressIn(full_name="X", phone="+1 415 555 2671", country="us", city="NYC", address_line="1 Main St")
    check("address country normalized to US", a.country == "US")
    try:
        AddressIn(full_name="X", phone="+1 415 555 2671", country="XX", city="NYC", address_line="1 Main St")
        check("unknown country rejected", False)
    except Exception:
        check("unknown country rejected", True)

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILURES:", FAIL)
        sys.exit(1)


asyncio.run(main())

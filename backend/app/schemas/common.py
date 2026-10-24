from typing import Optional
import phonenumbers
from pydantic import field_validator
from app.core.countries import is_valid_country


def normalize_phone_e164(value: str) -> str:
    """Validate an international phone number and normalize it to E.164.

    Accepts numbers with a leading '+' and country code (e.g. +14155552671).
    A default region is intentionally not applied: in a global deployment the
    country must come from the client, not be guessed server-side.
    """
    raw = (value or "").strip()
    try:
        parsed = phonenumbers.parse(raw, None)
    except phonenumbers.NumberParseException as exc:
        raise ValueError(
            "Phone number must include the country code, e.g. +14155552671"
        ) from exc
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("Invalid phone number for the given country code")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class PhoneMixin:
    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: str) -> str:
        return normalize_phone_e164(v)


class CountryMixin:
    @field_validator("country")
    @classmethod
    def _validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        code = v.strip().upper()
        if not is_valid_country(code):
            raise ValueError(f"Unsupported country code: {v!r}")
        return code

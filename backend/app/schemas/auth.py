from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.schemas.common import PhoneMixin


class CustomerRegister(PhoneMixin, BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class CustomerLogin(BaseModel):
    email: EmailStr
    password: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class TwoFAVerify(BaseModel):
    """Second login step. The temp_token binds this request to a password
    challenge that already succeeded; the code is a 6-digit TOTP or an
    8-character backup code."""
    temp_token: str = Field(..., min_length=20)
    code: str = Field(..., min_length=6, max_length=8)


class TwoFASetupConfirm(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class TwoFADisable(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class AdminLoginChallenge(BaseModel):
    """Returned when password is valid but 2FA is required."""
    requires_2fa: bool = True
    message: str = "Two-factor authentication required"
    temp_token: str  # short-lived, single-use token for the 2FA step


class RefreshRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True

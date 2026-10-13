from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, AliasChoices


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user: Optional[Dict[str, Any]] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., validation_alias=AliasChoices("refresh_token", "refreshToken"))


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, validation_alias=AliasChoices("refresh_token", "refreshToken"))


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class CustomerLoginRequest(BaseModel):
    email: str
    password: Optional[str] = None


class Customer2FaConfig(BaseModel):
    enabled: bool
    method: Optional[str] = "email"
    secret: Optional[str] = None
    backupCodes: Optional[List[str]] = None


class Customer2FaStatus(BaseModel):
    enabled: bool
    method: str = "email"
    hasSecret: bool = False
    secret: Optional[str] = None
    backupCodesCount: int = 0
    backupCodes: Optional[List[str]] = None
    confirmedAt: Optional[str] = None


class Customer2FaVerify(BaseModel):
    code: str
    email: Optional[EmailStr] = None


class Customer2FaSendCode(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None


class CustomerChangePassword(BaseModel):
    currentPassword: str
    newPassword: str

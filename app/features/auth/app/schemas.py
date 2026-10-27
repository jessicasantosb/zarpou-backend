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
    # Login SEM senha é proibido (OWASP A07): a senha é obrigatória e sempre verificada.
    password: str = Field(..., min_length=1)


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


class CustomerForgotPassword(BaseModel):
    email: EmailStr


class CustomerResetPassword(BaseModel):
    token: str = Field(..., min_length=10)
    # Mesma regra do cadastro: senha nova com no mínimo 6 caracteres
    password: str = Field(..., min_length=6)

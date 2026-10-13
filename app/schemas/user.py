from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "admin"
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomerBase(BaseModel):
    name: str = Field(..., validation_alias=AliasChoices("name", "fullName"))
    email: EmailStr
    phone: Optional[str] = None
    cpf: Optional[str] = None


class CustomerCreate(CustomerBase):
    password: Optional[str] = None


class CustomerAdminCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    cpf: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True


class CustomerAdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cpf: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerStatusUpdate(BaseModel):
    is_active: bool


class NotificationPreferencesSchema(BaseModel):
    whatsappPromotions: bool = True
    emailPromotions: bool = True
    updatedAt: Optional[str] = None


class CustomerUpdateNotifications(BaseModel):
    whatsappPromotions: Optional[bool] = None
    emailPromotions: Optional[bool] = None


class CustomerUpdateProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fullName: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    notification_whatsapp_promotions: bool = True
    notification_email_promotions: bool = True
    notification_updated_at: Optional[datetime] = None
    notifications: Optional[dict] = None
    total_bookings: Optional[int] = 0
    twoFactorEnabled: bool = False
    twoFactorMethod: Optional[str] = "email"
    twoFactorSecret: Optional[str] = None
    backupCodes: Optional[List[str]] = None
    twoFactorConfirmedAt: Optional[str] = None


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


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[dict] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., validation_alias=AliasChoices("refresh_token", "refreshToken"))


class LoginRequest(BaseModel):
    email: str
    password: str


class CustomerLoginRequest(BaseModel):
    email: str
    password: Optional[str] = None


class CustomerChangePassword(BaseModel):
    currentPassword: str
    newPassword: str

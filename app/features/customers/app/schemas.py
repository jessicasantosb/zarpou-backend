import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict, field_serializer, field_validator


def validate_cpf_digits(value: Optional[str]) -> Optional[str]:
    if not value or not str(value).strip():
        return None
    clean = re.sub(r"\D", "", str(value))
    if not clean:
        return None
    if len(clean) != 11:
        raise ValueError("O CPF deve conter exatamente 11 dígitos numéricos.")
    if clean == clean[0] * 11:
        raise ValueError("Número de CPF inválido.")

    # 1º dígito verificador
    s = sum(int(clean[i]) * (10 - i) for i in range(9))
    d1 = 11 - (s % 11)
    d1 = 0 if d1 >= 10 else d1
    if int(clean[9]) != d1:
        raise ValueError("Dígito verificador do CPF inválido.")

    # 2º dígito verificador
    s = sum(int(clean[i]) * (11 - i) for i in range(10))
    d2 = 11 - (s % 11)
    d2 = 0 if d2 >= 10 else d2
    if int(clean[10]) != d2:
        raise ValueError("Dígito verificador do CPF inválido.")

    return clean


class CustomerBase(BaseModel):
    name: str = Field(..., validation_alias=AliasChoices("name", "fullName"))
    email: EmailStr
    phone: Optional[str] = None
    cpf: Optional[str] = None


class CustomerCreate(CustomerBase):
    password: Optional[str] = None

    @field_validator("cpf", mode="before")
    @classmethod
    def validate_cpf(cls, v):
        return validate_cpf_digits(v)


class CustomerAdminCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    cpf: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True

    @field_validator("cpf", mode="before")
    @classmethod
    def validate_cpf(cls, v):
        return validate_cpf_digits(v)


class CustomerAdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    cpf: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("cpf", mode="before")
    @classmethod
    def validate_cpf(cls, v):
        return validate_cpf_digits(v)


class CustomerStatusUpdate(BaseModel):
    is_active: bool


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
    consent: Optional[dict] = None

    @field_serializer("twoFactorSecret")
    def _hide_totp_secret(self, _value: Optional[str]) -> None:
        # Segredo TOTP nunca é exposto em respostas genéricas (lista admin, /me, cadastro)
        return None


class CustomerConsentUpdate(BaseModel):
    """Registro de consentimento LGPD (Art. 8º): aceite explícito, versionado e com evidência."""
    acceptedPrivacyPolicy: bool
    acceptedTermsOfUse: bool
    version: str = Field("1.0", max_length=20)
    whatsappPromotions: Optional[bool] = None
    emailPromotions: Optional[bool] = None


class CustomerDeleteRequest(BaseModel):
    """Confirmação para exclusão/anonimização da conta (LGPD Art. 18 IV e VI)."""
    password: Optional[str] = None
    confirm: bool = False

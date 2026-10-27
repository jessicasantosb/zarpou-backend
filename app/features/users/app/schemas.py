from datetime import datetime
import json
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field, AliasChoices, field_validator


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    is_active: bool = True
    two_factor_enabled: Optional[bool] = Field(
        default=False,
        validation_alias=AliasChoices("two_factor_enabled", "twoFactorEnabled")
    )
    two_factor_method: Optional[str] = Field(
        default="email",
        validation_alias=AliasChoices("two_factor_method", "twoFactorMethod")
    )
    two_factor_secret: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_secret", "twoFactorSecret")
    )
    two_factor_backup_codes: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_backup_codes", "twoFactorBackupCodes", "backupCodes")
    )
    allowed_screens: Optional[List[str]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("allowed_screens", "allowedScreens")
    )


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    two_factor_enabled: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_enabled", "twoFactorEnabled")
    )
    two_factor_method: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_method", "twoFactorMethod")
    )
    two_factor_secret: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_secret", "twoFactorSecret")
    )
    two_factor_backup_codes: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("two_factor_backup_codes", "twoFactorBackupCodes", "backupCodes")
    )
    allowed_screens: Optional[List[str]] = Field(
        default=None,
        validation_alias=AliasChoices("allowed_screens", "allowedScreens")
    )


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    two_factor_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("two_factor_enabled", "twoFactorEnabled")
    )
    twoFactorEnabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("twoFactorEnabled", "two_factor_enabled")
    )
    two_factor_method: Optional[str] = Field(
        default="email",
        validation_alias=AliasChoices("two_factor_method", "twoFactorMethod")
    )
    twoFactorMethod: Optional[str] = Field(
        default="email",
        validation_alias=AliasChoices("twoFactorMethod", "two_factor_method")
    )
    # Campos twoFactorSecret/two_factor_secret/backupCodes foram removidos da
    # resposta (OWASP A07): vazavam o segredo TOTP e os códigos de recuperação de
    # TODOS os administradores para qualquer operador com a tela 'administradores'.
    allowed_screens: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("allowed_screens", "allowedScreens")
    )
    allowedScreens: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("allowedScreens", "allowed_screens")
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("allowed_screens", "allowedScreens", mode="before")
    @classmethod
    def validate_screens(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

import re
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{3,50}$")


class CouponBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=50, examples=["ZARPOU10"])
    description: Optional[str] = None
    discount_type: str = "percent"  # 'percent' | 'fixed'
    discount_value: float = Field(..., gt=0, examples=[10])
    min_order_amount: Optional[float] = Field(None, ge=0)
    max_uses: Optional[int] = Field(None, ge=1)
    used_count: int = Field(0, ge=0)
    per_customer_limit: int = Field(1, ge=1)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        code = v.strip().upper()
        if not CODE_PATTERN.match(code):
            raise ValueError(
                "O código do cupom deve conter de 3 a 50 caracteres: apenas letras, números, '-' ou '_'."
            )
        return code

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in ("percent", "fixed"):
            raise ValueError("O tipo de desconto deve ser 'percent' (percentual) ou 'fixed' (valor fixo).")
        return normalized


class CouponCreate(CouponBase):
    id: Optional[str] = None


class CouponUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    min_order_amount: Optional[float] = Field(None, ge=0)
    max_uses: Optional[int] = Field(None, ge=1)
    per_customer_limit: Optional[int] = Field(None, ge=1)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        code = v.strip().upper()
        if not CODE_PATTERN.match(code):
            raise ValueError(
                "O código do cupom deve conter de 3 a 50 caracteres: apenas letras, números, '-' ou '_'."
            )
        return code

    @field_validator("discount_type")
    @classmethod
    def validate_discount_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip().lower()
        if normalized not in ("percent", "fixed"):
            raise ValueError("O tipo de desconto deve ser 'percent' (percentual) ou 'fixed' (valor fixo).")
        return normalized


class CouponResponse(CouponBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_by: Optional[str] = None
    created_at: datetime
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None


class CouponGenerateRequest(BaseModel):
    """Pedido de geração de código aleatório para novo cupom."""

    prefix: Optional[str] = Field(None, max_length=20, examples=["BLACK"])
    length: int = Field(10, ge=4, le=30)


class CouponCodeResponse(BaseModel):
    code: str


class CouponValidateRequest(BaseModel):
    """Payload público de validação de cupom no checkout do cliente."""

    code: str = Field(..., min_length=1, max_length=50, examples=["ZARPOU10"])
    order_amount: Optional[float] = Field(None, ge=0, examples=[1200.0])
    customer_email: Optional[str] = Field(None, max_length=255)


class CouponValidateResponse(BaseModel):
    valid: bool = True
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    discount_amount: float = 0.0
    min_order_amount: Optional[float] = None
    valid_to: Optional[date] = None

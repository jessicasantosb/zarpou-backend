from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator
from app.features.hotels.app.schemas import HotelResponse, RoomResponse
from app.features.flights.app.schemas import FlightResponse
from app.features.packages.app.schemas import PackageResponse


class TravelerSchema(BaseModel):
    id: Optional[str] = None
    fullName: str
    documentType: str = "CPF"  # 'CPF', 'Passaporte'
    documentNumber: str
    birthDate: str
    gender: str = "M"  # 'M', 'F', 'Outro'
    email: EmailStr
    phone: str
    isPrimary: bool = False


class BookingAddonSchema(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    price: float
    category: str


class PriceSummarySchema(BaseModel):
    baseAmount: float
    taxesAndFees: float
    addonsAmount: float
    discountAmount: float
    finalAmount: float


class CreditCardDataSchema(BaseModel):
    """
    PCI DSS: o fluxo recomendado é o frontend tokenizar o cartão direto no gateway
    (ex.: Mercado Pago CardForm) e enviar apenas `cardToken`. Caso dados brutos ainda
    sejam enviados (legado), o PAN e o CVV são descartados logo após a validação,
    restando apenas os 4 últimos dígitos e a bandeira.
    """
    cardToken: Optional[str] = None
    cardLastFour: Optional[str] = None
    cardBrand: Optional[str] = None
    cardNumber: Optional[str] = Field(None, repr=False)
    holderName: Optional[str] = None
    expirationDate: Optional[str] = None
    cvv: Optional[str] = Field(None, repr=False)
    installments: int = 1

    @model_validator(mode="after")
    def _strip_sensitive_card_data(self):
        if self.cardNumber:
            digits = "".join(ch for ch in self.cardNumber if ch.isdigit())
            if digits and not self.cardLastFour:
                self.cardLastFour = digits[-4:]
            if digits and not self.cardBrand:
                self.cardBrand = _detect_card_brand(digits)
        # Nunca manter PAN completo nem CVV em memória/log/banco
        self.cardNumber = None
        self.cvv = None
        return self


def _detect_card_brand(digits: str) -> str:
    if digits.startswith("4"):
        return "visa"
    if digits[:2] in {"51", "52", "53", "54", "55"} or "2221" <= digits[:4] <= "2720":
        return "mastercard"
    if digits[:2] in {"34", "37"}:
        return "amex"
    if digits.startswith(("4011", "4312", "4389", "5041", "5067", "6277", "6362", "6363", "6504", "6505", "6516")):
        return "elo"
    if digits.startswith(("606282", "3841")):
        return "hipercard"
    return "desconhecida"


class BookingCreate(BaseModel):
    productType: str  # 'hotel', 'flight', 'package'
    hotelId: Optional[str] = None
    selectedRoomId: Optional[str] = None
    flightId: Optional[str] = None
    packageId: Optional[str] = None
    checkInDate: Optional[str] = None
    checkOutDate: Optional[str] = None
    nights: Optional[int] = None
    adults: int = 1
    children: int = 0
    travelers: List[TravelerSchema]
    addons: Optional[List[BookingAddonSchema]] = []
    paymentMethod: str = "credit_card"  # 'credit_card', 'pix', 'boleto', 'corporate_invoice'
    installments: int = 1
    creditCard: Optional[CreditCardDataSchema] = None
    companyId: Optional[str] = None
    costCenter: Optional[str] = None
    couponCode: Optional[str] = None  # cupom de desconto aplicado no checkout


class BookingStatusUpdate(BaseModel):
    status: str  # 'confirmada', 'pendente_pagamento', 'cancelada', 'concluida'


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    locatorCode: str
    locator: Optional[str] = None
    createdAt: datetime
    status: str
    productType: str
    checkInDate: Optional[date] = None
    checkOutDate: Optional[date] = None
    nights: Optional[int] = None
    paymentMethod: str
    installments: int
    companyId: Optional[str] = None
    costCenter: Optional[str] = None
    couponCode: Optional[str] = None
    pricing: PriceSummarySchema
    pixCode: Optional[str] = None
    pixQrCodeUrl: Optional[str] = None
    pixExpiresAt: Optional[datetime] = None
    boletoBarcode: Optional[str] = None
    voucherUrl: Optional[str] = None
    travelers: List[TravelerSchema] = []
    addons: List[BookingAddonSchema] = []
    hotel: Optional[HotelResponse] = None
    selectedRoom: Optional[RoomResponse] = None
    flight: Optional[FlightResponse] = None
    packageItem: Optional[PackageResponse] = None

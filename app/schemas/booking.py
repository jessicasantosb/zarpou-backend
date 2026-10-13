from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.schemas.hotel import HotelResponse, RoomResponse
from app.schemas.flight import FlightResponse
from app.schemas.package import PackageResponse


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
    cardNumber: Optional[str] = None
    holderName: Optional[str] = None
    expirationDate: Optional[str] = None
    cvv: Optional[str] = None
    installments: int = 1


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

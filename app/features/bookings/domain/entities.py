from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class PriceSummaryEntity:
    base_amount: Decimal = Decimal("0.00")
    taxes_and_fees: Decimal = Decimal("0.00")
    addons_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    final_amount: Decimal = Decimal("0.00")


@dataclass
class BookingTravelerEntity:
    id: str
    booking_id: str
    full_name: str
    document_type: str
    document_number: str
    birth_date: date
    gender: str
    email: str
    phone: str
    is_primary: bool = False
    created_at: Optional[datetime] = None


@dataclass
class BookingAddonEntity:
    id: str
    booking_id: str
    title: str
    price: Decimal
    category: str
    addon_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class BookingEntity:
    id: str
    locator_code: str
    product_type: str
    status: str
    payment_method: str
    pricing: PriceSummaryEntity
    customer_id: Optional[str] = None
    company_id: Optional[str] = None
    cost_center: Optional[str] = None
    hotel_id: Optional[str] = None
    room_id: Optional[str] = None
    flight_id: Optional[str] = None
    package_id: Optional[str] = None
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    nights: Optional[int] = None
    adults_count: int = 1
    children_count: int = 0
    installments: int = 1
    pix_code: Optional[str] = None
    pix_qr_code_url: Optional[str] = None
    pix_expires_at: Optional[datetime] = None
    boleto_barcode: Optional[str] = None
    voucher_url: Optional[str] = None
    created_at: Optional[datetime] = None
    travelers: List[BookingTravelerEntity] = field(default_factory=list)
    addons: List[BookingAddonEntity] = field(default_factory=list)

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class RoomEntity:
    id: str
    hotel_id: str
    name: str
    description: Optional[str] = None
    max_adults: int = 2
    max_children: int = 0
    beds: Optional[str] = None
    size_m2: Optional[int] = None
    price_per_night: Decimal = Decimal("0.00")
    original_price_per_night: Optional[Decimal] = None
    free_cancellation: bool = True
    breakfast_included: bool = True
    available_rooms: int = 5
    image_url: Optional[str] = None
    amenities: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None


@dataclass
class HotelEntity:
    id: str
    name: str
    city: str
    image_url: str
    base_price_per_night: Decimal
    state: Optional[str] = None
    country: str = "Brasil"
    stars: int = 4
    rating: Decimal = Decimal("9.0")
    review_count: int = 0
    review_label: str = "Excelente"
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    description: Optional[str] = None
    gallery: List[str] = field(default_factory=list)
    amenities: List[str] = field(default_factory=list)
    original_price_per_night: Optional[Decimal] = None
    discount_percent: int = 0
    max_installments: int = 12
    badges: List[str] = field(default_factory=list)
    featured: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    rooms: List[RoomEntity] = field(default_factory=list)

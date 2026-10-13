from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from app.features.hotels.domain.entities import HotelEntity
from app.features.flights.domain.entities import FlightEntity


@dataclass
class PackageEntity:
    id: str
    title: str
    destination_city: str
    price_per_person: Decimal
    image_url: str
    duration_nights: int = 3
    hotel_id: Optional[str] = None
    flight_id: Optional[str] = None
    original_price_per_person: Optional[Decimal] = None
    discount_percent: int = 0
    max_installments: int = 12
    highlights: List[str] = field(default_factory=list)
    featured: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    hotel: Optional[HotelEntity] = None
    flight: Optional[FlightEntity] = None

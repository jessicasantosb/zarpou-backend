from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class FlightSegmentEntity:
    id: str
    flight_id: str
    segment_type: str
    flight_number: str
    airline: str
    airline_code: str
    origin_iata: str
    origin_city: str
    origin_airport: str
    destination_iata: str
    destination_city: str
    destination_airport: str
    departure_date: date
    departure_time: str
    arrival_date: date
    arrival_time: str
    airline_logo: Optional[str] = None
    duration: Optional[str] = None
    stops: int = 0
    stop_city: Optional[str] = None
    cabin_class: str = "Econômica"
    baggage_included: bool = True
    hand_baggage_included: bool = True
    created_at: Optional[datetime] = None


@dataclass
class FlightEntity:
    id: str
    price: Decimal
    original_price: Optional[Decimal] = None
    discount_percent: int = 0
    max_installments: int = 12
    is_round_trip: bool = True
    featured: bool = False
    country: Optional[str] = None
    flag: Optional[str] = None
    region: str = "all"
    image_url: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    segments: List[FlightSegmentEntity] = field(default_factory=list)

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class FlightSegmentBase(BaseModel):
    segment_type: str  # 'outbound' ou 'return'
    flight_number: str
    airline: str
    airline_code: str
    airline_logo: Optional[str] = None
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
    duration: Optional[str] = None
    stops: int = 0
    stop_city: Optional[str] = None
    cabin_class: str = "Econômica"
    baggage_included: bool = True
    hand_baggage_included: bool = True


class FlightSegmentCreate(FlightSegmentBase):
    id: str
    flight_id: str


class FlightSegmentResponse(FlightSegmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    flight_id: str
    created_at: datetime


class FlightBase(BaseModel):
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[int] = 0
    max_installments: int = 12
    is_round_trip: bool = True
    featured: bool = False
    country: Optional[str] = None
    flag: Optional[str] = None
    region: str = "all"  # 'all', 'usa', 'europe', 'south-america', 'other'
    image_url: Optional[str] = None
    highlights: Optional[List[str]] = []
    is_active: bool = True


class FlightCreate(FlightBase):
    id: str
    outbound: FlightSegmentBase
    return_flight: Optional[FlightSegmentBase] = None


class FlightUpdate(BaseModel):
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[int] = None
    max_installments: Optional[int] = None
    is_round_trip: Optional[bool] = None
    featured: Optional[bool] = None
    country: Optional[str] = None
    flag: Optional[str] = None
    region: Optional[str] = None
    image_url: Optional[str] = None
    highlights: Optional[List[str]] = None
    is_active: Optional[bool] = None


class FlightResponse(FlightBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    segments: List[FlightSegmentResponse] = []

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.hotel import HotelResponse
from app.schemas.flight import FlightResponse


class PackageBase(BaseModel):
    title: str
    destination_city: str
    duration_nights: int = 3
    hotel_id: Optional[str] = None
    flight_id: Optional[str] = None
    price_per_person: float
    original_price_per_person: Optional[float] = None
    discount_percent: Optional[int] = 0
    max_installments: int = 12
    image_url: str
    highlights: Optional[List[str]] = []
    featured: bool = False
    is_active: bool = True


class PackageCreate(PackageBase):
    id: str


class PackageResponse(PackageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    hotel: Optional[HotelResponse] = None
    flight: Optional[FlightResponse] = None

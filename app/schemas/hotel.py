from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RoomBase(BaseModel):
    name: str
    description: Optional[str] = None
    max_adults: int = 2
    max_children: int = 0
    beds: Optional[str] = None
    size_m2: Optional[int] = None
    price_per_night: float
    original_price_per_night: Optional[float] = None
    free_cancellation: bool = True
    breakfast_included: bool = True
    available_rooms: int = 5
    image_url: Optional[str] = None
    amenities: Optional[List[str]] = []


class RoomCreate(RoomBase):
    id: str
    hotel_id: str


class RoomResponse(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    hotel_id: str
    created_at: datetime


class HotelBase(BaseModel):
    name: str
    city: str
    state: Optional[str] = None
    country: str = "Brasil"
    stars: int = 4
    rating: float = 9.0
    review_count: int = 0
    review_label: str = "Excelente"
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    description: Optional[str] = None
    image_url: str
    gallery: Optional[List[str]] = []
    amenities: Optional[List[str]] = []
    base_price_per_night: float
    original_price_per_night: Optional[float] = None
    discount_percent: Optional[int] = 0
    max_installments: int = 12
    badges: Optional[List[str]] = []
    featured: bool = False
    is_active: bool = True


class HotelCreate(HotelBase):
    id: str
    rooms: Optional[List[RoomBase]] = []


class HotelUpdate(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    stars: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    review_label: Optional[str] = None
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    gallery: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    base_price_per_night: Optional[float] = None
    original_price_per_night: Optional[float] = None
    discount_percent: Optional[int] = None
    max_installments: Optional[int] = None
    badges: Optional[List[str]] = None
    featured: Optional[bool] = None
    is_active: Optional[bool] = None


class HotelResponse(HotelBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    rooms: List[RoomResponse] = []

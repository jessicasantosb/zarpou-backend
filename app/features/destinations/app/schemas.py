from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DestinationBase(BaseModel):
    title: str
    country: str
    flag: Optional[str] = None
    category: str = "all"  # 'all', 'national', 'international'
    tag: Optional[str] = None
    description: Optional[str] = None
    starting_price: float = 0.0
    accommodations_count: int = 0
    link: Optional[str] = None
    image_url: str
    is_active: bool = True
    display_order: int = 0


class DestinationCreate(DestinationBase):
    id: str


class DestinationUpdate(BaseModel):
    title: Optional[str] = None
    country: Optional[str] = None
    flag: Optional[str] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    starting_price: Optional[float] = None
    accommodations_count: Optional[int] = None
    link: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class DestinationResponse(DestinationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime

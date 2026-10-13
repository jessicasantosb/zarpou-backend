from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PromotionBase(BaseModel):
    title: str
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    discount_text: Optional[str] = None
    image_url: str
    link: str
    button_text: str = "Aproveitar Oferta"
    active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    display_order: int = 0
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None


class PromotionCreate(PromotionBase):
    id: Optional[str] = None


class PromotionUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    discount_text: Optional[str] = None
    image_url: Optional[str] = None
    link: Optional[str] = None
    button_text: Optional[str] = None
    active: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    display_order: Optional[int] = None
    notification_sent: Optional[bool] = None
    notification_sent_at: Optional[datetime] = None


class PromotionResponse(PromotionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime

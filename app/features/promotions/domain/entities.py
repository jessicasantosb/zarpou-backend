from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class PromotionEntity:
    id: str
    title: str
    subtitle: Optional[str] = None
    badge: Optional[str] = None
    discount_text: Optional[str] = None
    image_url: str = ""
    link: str = ""
    button_text: str = "Aproveitar Oferta"
    active: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    display_order: int = 0
    notification_sent: bool = False
    notification_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

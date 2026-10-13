from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class DestinationEntity:
    id: str
    title: str
    country: str
    flag: Optional[str] = None
    category: str = "all"
    tag: Optional[str] = None
    description: Optional[str] = None
    starting_price: Decimal = Decimal("0.00")
    accommodations_count: int = 0
    link: Optional[str] = None
    image_url: str = ""
    is_active: bool = True
    display_order: int = 0
    created_at: Optional[datetime] = None

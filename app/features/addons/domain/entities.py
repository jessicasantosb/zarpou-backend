from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class AddonEntity:
    id: str
    title: str
    description: Optional[str]
    price: Decimal
    category: str
    is_active: bool = True
    created_at: Optional[datetime] = None

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List


@dataclass
class CustomerEntity:
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    cpf: Optional[str] = None
    birth_date: Optional[date] = None
    is_active: bool = True
    two_factor_enabled: bool = False
    two_factor_method: Optional[str] = "email"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

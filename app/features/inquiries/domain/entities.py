from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ContactInquiryEntity:
    id: str
    name: str
    email: str
    phone: str
    destination: str
    start_date: date
    end_date: date
    travel_type: str
    accommodation_preference: str
    room_type: str
    meal_plan: str
    transportation: str
    internal_transportation: str
    estimated_budget: Decimal
    number_of_adults: int = 1
    number_of_children: int = 0
    dietary_restrictions: Optional[str] = None
    other_special_needs: Optional[str] = None
    additional_info: Optional[str] = None
    status: str = "novo"
    admin_notes: Optional[str] = None
    created_at: Optional[datetime] = None

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict


class InquiryCreate(BaseModel):
    name: str = Field(..., validation_alias=AliasChoices("name", "fullName"))
    email: EmailStr
    phone: str
    destination: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    numberOfAdults: Optional[str] = "2"
    numberOfChildren: Optional[str] = "0"
    travelType: Optional[str] = "leisure"
    accommodationPreference: Optional[str] = "hotel"
    roomType: Optional[str] = "standard"
    mealPlan: Optional[str] = "cafe_manha"
    transportation: Optional[str] = "aereo"
    internalTransportation: Optional[str] = "nenhum"
    estimatedBudget: Optional[str] = "5000"
    dietaryRestrictions: Optional[str] = None
    otherSpecialNeeds: Optional[str] = None
    additionalInfo: Optional[str] = None


class InquiryStatusUpdate(BaseModel):
    status: str  # 'novo', 'em_atendimento', 'orcamento_enviado', 'fechado', 'perdido'
    admin_notes: Optional[str] = None


class InquiryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    phone: str
    destination: str
    start_date: date
    end_date: date
    number_of_adults: int
    number_of_children: int
    travel_type: str
    accommodation_preference: str
    room_type: str
    meal_plan: str
    transportation: str
    internal_transportation: str
    estimated_budget: float
    dietary_restrictions: Optional[str] = None
    other_special_needs: Optional[str] = None
    additional_info: Optional[str] = None
    status: str
    admin_notes: Optional[str] = None
    created_at: datetime

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AddonBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str  # 'seguro', 'bagagem', 'traslado', 'outro'
    is_active: bool = True


class AddonCreate(AddonBase):
    id: str


class AddonResponse(AddonBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime

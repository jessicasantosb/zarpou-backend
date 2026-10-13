from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Text
from app.core.database import Base


class Addon(Base):
    __tablename__ = "addons"

    id = Column(String(50), primary_key=True)  # ex: 'addon-insurance'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=False)  # 'seguro', 'bagagem', 'traslado', 'outro'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


AddonModel = Addon

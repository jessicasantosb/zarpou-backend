from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text
from app.core.database import Base


class Destination(Base):
    __tablename__ = "destinations"

    id = Column(String(50), primary_key=True)  # ex: 'dest-dubai'
    title = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    flag = Column(String(20), nullable=True)
    category = Column(String(50), nullable=False, default="all")  # 'all', 'national', 'international'
    tag = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    starting_price = Column(Numeric(10, 2), nullable=False, default=0.00)
    accommodations_count = Column(Integer, nullable=False, default=0)
    link = Column(String(255), nullable=True)
    image_url = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Package(Base):
    __tablename__ = "packages"

    id = Column(String(50), primary_key=True)
    title = Column(String(255), nullable=False)
    destination_city = Column(String(100), nullable=False)
    duration_nights = Column(Integer, nullable=False, default=3)
    hotel_id = Column(String(50), ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True)
    flight_id = Column(String(50), ForeignKey("flights.id", ondelete="SET NULL"), nullable=True)
    price_per_person = Column(Numeric(10, 2), nullable=False)
    original_price_per_person = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Integer, default=0)
    max_installments = Column(Integer, nullable=False, default=12)
    image_url = Column(Text, nullable=False)
    highlights = Column(JSON, nullable=True)  # List[str]
    featured = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel")
    flight = relationship("Flight")
    bookings = relationship("Booking", back_populates="package_item")

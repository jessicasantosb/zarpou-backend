from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(String(50), primary_key=True)  # ex: 'hotel-rio-copacabana'
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=True)
    country = Column(String(100), nullable=False, default="Brasil")
    stars = Column(Integer, nullable=False, default=4)
    rating = Column(Numeric(3, 1), nullable=False, default=9.0)
    review_count = Column(Integer, nullable=False, default=0)
    review_label = Column(String(50), nullable=False, default="Excelente")
    address = Column(String(255), nullable=True)
    neighborhood = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=False)
    gallery = Column(JSON, nullable=True)  # List[str]
    amenities = Column(JSON, nullable=True)  # List[str]
    base_price_per_night = Column(Numeric(10, 2), nullable=False)
    original_price_per_night = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Integer, default=0)
    max_installments = Column(Integer, nullable=False, default=12)
    badges = Column(JSON, nullable=True)  # List[str]
    featured = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    rooms = relationship("Room", back_populates="hotel", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="hotel")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(50), primary_key=True)  # ex: 'room-copa-standard'
    hotel_id = Column(String(50), ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_adults = Column(Integer, nullable=False, default=2)
    max_children = Column(Integer, nullable=False, default=0)
    beds = Column(String(150), nullable=True)
    size_m2 = Column(Integer, nullable=True)
    price_per_night = Column(Numeric(10, 2), nullable=False)
    original_price_per_night = Column(Numeric(10, 2), nullable=True)
    free_cancellation = Column(Boolean, nullable=False, default=True)
    breakfast_included = Column(Boolean, nullable=False, default=True)
    available_rooms = Column(Integer, nullable=False, default=5)
    image_url = Column(Text, nullable=True)
    amenities = Column(JSON, nullable=True)  # List[str]
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    hotel = relationship("Hotel", back_populates="rooms")
    bookings = relationship("Booking", back_populates="selected_room")

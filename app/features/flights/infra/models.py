from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Text, JSON, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class Flight(Base):
    __tablename__ = "flights"

    id = Column(String(50), primary_key=True)  # ex: 'flight-bh-miami'
    price = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)
    discount_percent = Column(Integer, default=0)
    max_installments = Column(Integer, nullable=False, default=12)
    is_round_trip = Column(Boolean, nullable=False, default=True)
    featured = Column(Boolean, nullable=False, default=False)
    country = Column(String(100), nullable=True)
    flag = Column(String(20), nullable=True)
    region = Column(String(50), nullable=False, default="all")  # 'all', 'usa', 'europe', 'south-america', 'other'
    image_url = Column(Text, nullable=True)
    highlights = Column(JSON, nullable=True)  # List[str]
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    segments = relationship("FlightSegment", back_populates="flight", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="flight")


class FlightSegment(Base):
    __tablename__ = "flight_segments"

    id = Column(String(50), primary_key=True)
    flight_id = Column(String(50), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_type = Column(String(20), nullable=False)  # 'outbound' ou 'return'
    flight_number = Column(String(30), nullable=False)
    airline = Column(String(100), nullable=False)
    airline_code = Column(String(10), nullable=False)  # 'LA', 'G3', 'AD', etc.
    airline_logo = Column(Text, nullable=True)
    origin_iata = Column(String(10), nullable=False, index=True)
    origin_city = Column(String(100), nullable=False)
    origin_airport = Column(String(255), nullable=False)
    destination_iata = Column(String(10), nullable=False, index=True)
    destination_city = Column(String(100), nullable=False)
    destination_airport = Column(String(255), nullable=False)
    departure_date = Column(Date, nullable=False)
    departure_time = Column(String(10), nullable=False)  # '10:15'
    arrival_date = Column(Date, nullable=False)
    arrival_time = Column(String(10), nullable=False)  # '18:40'
    duration = Column(String(50), nullable=True)  # '9h 25m'
    stops = Column(Integer, nullable=False, default=0)
    stop_city = Column(String(100), nullable=True)
    cabin_class = Column(String(50), nullable=False, default="Econômica")
    baggage_included = Column(Boolean, nullable=False, default=True)
    hand_baggage_included = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    flight = relationship("Flight", back_populates="segments")

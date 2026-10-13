from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Numeric, Text, ForeignKey, Date, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(50), primary_key=True)  # ex: 'booking-1718000000'
    locator_code = Column(String(20), nullable=False, unique=True, index=True)  # 'ZRP-849201'
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    company_id = Column(String(50), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    cost_center = Column(String(100), nullable=True)
    product_type = Column(String(20), nullable=False)  # 'hotel', 'flight', 'package'
    status = Column(
        String(30),
        nullable=False,
        default="pendente_pagamento",
        index=True
    )  # 'confirmada', 'pendente_pagamento', 'cancelada', 'concluida'

    # Relacionamento com produtos
    hotel_id = Column(String(50), ForeignKey("hotels.id", ondelete="SET NULL"), nullable=True)
    room_id = Column(String(50), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    flight_id = Column(String(50), ForeignKey("flights.id", ondelete="SET NULL"), nullable=True)
    package_id = Column(String(50), ForeignKey("packages.id", ondelete="SET NULL"), nullable=True)

    # Datas e capacidade
    check_in_date = Column(Date, nullable=True)
    check_out_date = Column(Date, nullable=True)
    nights = Column(Integer, nullable=True)
    adults_count = Column(Integer, nullable=False, default=1)
    children_count = Column(Integer, nullable=False, default=0)

    # Pagamento
    payment_method = Column(String(30), nullable=False)  # 'credit_card', 'pix', 'boleto'
    installments = Column(Integer, nullable=False, default=1)

    # Preços
    base_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    taxes_and_fees = Column(Numeric(10, 2), nullable=False, default=0.00)
    addons_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    final_amount = Column(Numeric(10, 2), nullable=False, default=0.00)

    # Faturamento e Vouchers
    pix_code = Column(Text, nullable=True)
    pix_qr_code_url = Column(Text, nullable=True)
    pix_expires_at = Column(DateTime(timezone=True), nullable=True)
    boleto_barcode = Column(String(100), nullable=True)
    voucher_url = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    customer = relationship("Customer", back_populates="bookings")
    company = relationship("Company", back_populates="bookings")
    hotel = relationship("Hotel", back_populates="bookings")
    selected_room = relationship("Room", back_populates="bookings")
    flight = relationship("Flight", back_populates="bookings")
    package_item = relationship("Package", back_populates="bookings")
    travelers = relationship("BookingTraveler", back_populates="booking", cascade="all, delete-orphan")
    addons = relationship("BookingAddon", back_populates="booking", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")


class BookingTraveler(Base):
    __tablename__ = "booking_travelers"

    id = Column(String(50), primary_key=True)
    booking_id = Column(String(50), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    document_type = Column(String(20), nullable=False, default="CPF")  # 'CPF', 'Passaporte'
    document_number = Column(String(50), nullable=False)
    birth_date = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)  # 'M', 'F', 'Outro'
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking", back_populates="travelers")


class BookingAddon(Base):
    __tablename__ = "booking_addons"

    id = Column(String(50), primary_key=True)
    booking_id = Column(String(50), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    addon_id = Column(String(50), ForeignKey("addons.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    booking = relationship("Booking", back_populates="addons")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(50), primary_key=True)
    booking_id = Column(String(50), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_method = Column(String(30), nullable=False)
    gateway_provider = Column(String(50), nullable=False, default="mercadopago")
    transaction_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="pending")  # 'pending', 'approved', 'rejected', 'refunded'
    amount = Column(Numeric(10, 2), nullable=False)
    installments = Column(Integer, nullable=False, default=1)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    raw_response = Column(JSON, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    booking = relationship("Booking", back_populates="payments")

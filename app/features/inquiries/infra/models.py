from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Integer, Numeric, Text, Date
from app.core.database import Base


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(String(50), primary_key=True, default=lambda: f"inq-{uuid.uuid4().hex[:12]}")
    
    # Usuário (step-user)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=False)
    
    # Destino e Datas (step-destination-info)
    destination = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    number_of_adults = Column(Integer, nullable=False, default=1)
    number_of_children = Column(Integer, nullable=False, default=0)
    travel_type = Column(String(100), nullable=False)
    
    # Preferências de Viagem (step-travel-info)
    accommodation_preference = Column(String(100), nullable=False)
    room_type = Column(String(100), nullable=False)
    meal_plan = Column(String(100), nullable=False)
    transportation = Column(String(100), nullable=False)
    internal_transportation = Column(String(100), nullable=False)
    estimated_budget = Column(Numeric(10, 2), nullable=False)
    dietary_restrictions = Column(Text, nullable=True)
    other_special_needs = Column(Text, nullable=True)
    additional_info = Column(Text, nullable=True)
    
    # Status administrativo
    status = Column(String(30), nullable=False, default="novo", index=True)  # 'novo', 'em_atendimento', 'orcamento_enviado', 'fechado', 'perdido'
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

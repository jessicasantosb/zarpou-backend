from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Date
from app.core.database import Base


class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(String(50), primary_key=True)  # ex: 'promo-1'
    title = Column(String(255), nullable=False)
    subtitle = Column(Text, nullable=True)
    badge = Column(String(100), nullable=True)  # 'OFERTA RELÂMPAGO', 'MAIS BUSCADO'
    discount_text = Column(String(100), nullable=True)  # 'Até 35% OFF'
    image_url = Column(Text, nullable=False)
    link = Column(String(255), nullable=False)
    button_text = Column(String(100), nullable=False, default="Aproveitar Oferta")
    active = Column(Boolean, nullable=False, default=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Date, Numeric
from app.core.database import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(50), primary_key=True)  # ex: 'cpn-1'
    code = Column(String(50), unique=True, nullable=False, index=True)  # ex: 'ZARPOU10'
    description = Column(Text, nullable=True)
    discount_type = Column(String(20), nullable=False, default="percent")  # 'percent' | 'fixed'
    discount_value = Column(Numeric(10, 2), nullable=False)  # % ou valor em R$
    min_order_amount = Column(Numeric(10, 2), nullable=True)  # valor mínimo do pedido
    max_uses = Column(Integer, nullable=True)  # None = usos ilimitados
    used_count = Column(Integer, nullable=False, default=0)
    per_customer_limit = Column(Integer, nullable=False, default=1)  # usos por cliente
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(36), nullable=True)  # id do admin que criou o cupom
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

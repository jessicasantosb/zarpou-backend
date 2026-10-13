from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(50), primary_key=True, default=lambda: f"comp-{uuid.uuid4().hex[:12]}")
    cnpj = Column(String(30), unique=True, nullable=False, index=True)
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=False)
    corporate_email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=False)
    manager_name = Column(String(255), nullable=False)
    manager_cpf = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Status e Políticas Comerciais
    status = Column(String(30), nullable=False, default="pendente", index=True)  # 'pendente', 'aprovada', 'bloqueada'
    corporate_discount_percent = Column(Numeric(5, 2), nullable=False, default=0.00)
    credit_limit = Column(Numeric(10, 2), nullable=False, default=0.00)
    credit_used = Column(Numeric(10, 2), nullable=False, default=0.00)
    payment_terms = Column(String(30), nullable=False, default="faturado_30d")  # 'faturado_15d', 'faturado_30d', 'cartao_corporativo'
    estimated_monthly_spend = Column(Numeric(10, 2), nullable=False, default=0.00)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    employees = relationship("CompanyEmployee", back_populates="company", cascade="all, delete-orphan")
    invoices = relationship("CompanyInvoice", back_populates="company", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="company")

    @property
    def credit_available(self) -> float:
        limit = float(self.credit_limit or 0.0)
        used = float(self.credit_used or 0.0)
        return max(0.0, round(limit - used, 2))


class CompanyEmployee(Base):
    __tablename__ = "company_employees"

    id = Column(String(50), primary_key=True, default=lambda: f"emp-{uuid.uuid4().hex[:12]}")
    company_id = Column(String(50), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    cpf = Column(String(20), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    cost_center = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="employees")


class CompanyInvoice(Base):
    __tablename__ = "company_invoices"

    id = Column(String(50), primary_key=True, default=lambda: f"inv-{uuid.uuid4().hex[:12]}")
    company_id = Column(String(50), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    due_date = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="aberta", index=True)  # 'aberta', 'fechada', 'paga', 'vencida'
    boleto_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    company = relationship("Company", back_populates="invoices")

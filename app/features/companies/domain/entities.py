from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class CompanyEntity:
    id: str
    cnpj: str
    razao_social: str
    nome_fantasia: str
    corporate_email: str
    phone: str
    manager_name: str
    manager_cpf: str
    status: str = "pendente"
    corporate_discount_percent: Decimal = Decimal("0.00")
    credit_limit: Decimal = Decimal("0.00")
    credit_used: Decimal = Decimal("0.00")
    payment_terms: str = "faturado_30d"
    estimated_monthly_spend: Decimal = Decimal("0.00")
    created_at: Optional[datetime] = None


@dataclass
class CompanyEmployeeEntity:
    id: str
    company_id: str
    full_name: str
    cpf: str
    email: str
    phone: Optional[str] = None
    cost_center: Optional[str] = None
    department: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class CompanyInvoiceEntity:
    id: str
    company_id: str
    invoice_number: str
    period_start: date
    period_end: date
    total_amount: Decimal
    due_date: date
    status: str = "aberta"
    boleto_url: Optional[str] = None
    created_at: Optional[datetime] = None

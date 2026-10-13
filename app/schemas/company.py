from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, AliasChoices, ConfigDict


class CompanyRegisterRequest(BaseModel):
    cnpj: str
    razaoSocial: str
    nomeFantasia: str
    corporateEmail: EmailStr
    phone: str
    managerName: str
    managerCpf: str
    password: str
    estimatedMonthlySpend: Optional[float] = 0.0


class CompanyLoginRequest(BaseModel):
    login: str = Field(..., validation_alias=AliasChoices("login", "corporateEmail", "email", "cnpj"))
    password: str


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cnpj: str
    razaoSocial: str
    nomeFantasia: str
    corporateEmail: str
    phone: str
    managerName: str
    managerCpf: str
    status: str  # 'pendente', 'aprovada', 'bloqueada'
    corporateDiscountPercent: float
    creditLimit: float
    creditUsed: float
    creditAvailable: float
    paymentTerms: str
    createdAt: datetime


class CompanyTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    company: CompanyResponse


class CompanyEmployeeCreate(BaseModel):
    fullName: str
    cpf: str
    email: EmailStr
    phone: Optional[str] = None
    costCenter: Optional[str] = None
    department: Optional[str] = None


class CompanyEmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    companyId: str
    fullName: str
    cpf: str
    email: str
    phone: Optional[str] = None
    costCenter: Optional[str] = None
    department: Optional[str] = None
    isActive: bool
    createdAt: datetime


class CompanyInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    companyId: str
    invoiceNumber: str
    periodStart: date
    periodEnd: date
    totalAmount: float
    dueDate: date
    status: str
    boletoUrl: Optional[str] = None
    createdAt: datetime


class CompanyAdminApprovalRequest(BaseModel):
    status: Optional[str] = None  # 'aprovada', 'pendente', 'bloqueada'
    corporateDiscountPercent: Optional[float] = None
    creditLimit: Optional[float] = None
    paymentTerms: Optional[str] = None

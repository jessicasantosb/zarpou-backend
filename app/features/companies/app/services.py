import re
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from app.features.companies.infra.models import Company, CompanyEmployee, CompanyInvoice
from app.features.companies.infra.repositories import (
    CompanyRepository,
    CompanyEmployeeRepository,
    CompanyInvoiceRepository,
)
from app.features.companies.app.schemas import (
    CompanyRegisterRequest,
    CompanyLoginRequest,
    CompanyAdminApprovalRequest,
    CompanyEmployeeCreate,
)


class CompanyService:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.employee_repo = CompanyEmployeeRepository(db)
        self.invoice_repo = CompanyInvoiceRepository(db)

    @staticmethod
    def format_company(c: Company) -> Dict[str, Any]:
        return {
            "id": c.id,
            "cnpj": c.cnpj,
            "razaoSocial": c.razao_social,
            "nomeFantasia": c.nome_fantasia,
            "corporateEmail": c.corporate_email,
            "phone": c.phone,
            "managerName": c.manager_name,
            "managerCpf": c.manager_cpf,
            "status": c.status,
            "corporateDiscountPercent": float(c.corporate_discount_percent or 0.0),
            "creditLimit": float(c.credit_limit or 0.0),
            "creditUsed": float(c.credit_used or 0.0),
            "creditAvailable": c.credit_available,
            "paymentTerms": c.payment_terms,
            "createdAt": c.created_at,
        }

    @staticmethod
    def format_employee(e: CompanyEmployee) -> Dict[str, Any]:
        return {
            "id": e.id,
            "companyId": e.company_id,
            "fullName": e.full_name,
            "cpf": e.cpf,
            "email": e.email,
            "phone": e.phone,
            "costCenter": e.cost_center,
            "department": e.department,
            "isActive": e.is_active,
            "createdAt": e.created_at,
        }

    @staticmethod
    def format_invoice(inv: CompanyInvoice) -> Dict[str, Any]:
        return {
            "id": inv.id,
            "companyId": inv.company_id,
            "invoiceNumber": inv.invoice_number,
            "periodStart": inv.period_start,
            "periodEnd": inv.period_end,
            "totalAmount": float(inv.total_amount or 0.0),
            "dueDate": inv.due_date,
            "status": inv.status,
            "boletoUrl": inv.boleto_url,
            "createdAt": inv.created_at,
        }

    def register(self, reg_in: CompanyRegisterRequest) -> Dict[str, Any]:
        clean_cnpj = re.sub(r"\D", "", reg_in.cnpj)
        if self.company_repo.get_by_cnpj(clean_cnpj):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma empresa cadastrada com este CNPJ."
            )

        clean_email = reg_in.corporateEmail.strip().lower()
        if self.company_repo.get_by_email(clean_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe uma empresa cadastrada com este e-mail corporativo."
            )

        company = Company(
            cnpj=clean_cnpj,
            razao_social=reg_in.razaoSocial.strip(),
            nome_fantasia=reg_in.nomeFantasia.strip(),
            corporate_email=clean_email,
            phone=reg_in.phone.strip(),
            manager_name=reg_in.managerName.strip(),
            manager_cpf=re.sub(r"\D", "", reg_in.managerCpf),
            password_hash=get_password_hash(reg_in.password),
            estimated_monthly_spend=reg_in.estimatedMonthlySpend or 0.0,
            status="pendente",
            corporate_discount_percent=5.00,
            credit_limit=0.00,
            credit_used=0.00,
            payment_terms="faturado_30d",
        )
        created = self.company_repo.create(company)
        return self.format_company(created)

    def login(self, login_in: CompanyLoginRequest) -> Dict[str, Any]:
        login_clean = login_in.login.strip().lower()
        login_digits = re.sub(r"\D", "", login_in.login)

        company = self.company_repo.get_by_login(login_clean, login_digits)
        if not company or not verify_password(login_in.password, company.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CNPJ/E-mail ou senha incorretos."
            )

        if company.status == "bloqueada":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta corporativa suspensa ou bloqueada. Entre em contato com a Zarpou."
            )

        access_token = create_access_token(subject=company.id, role="company")
        refresh_token = create_refresh_token(subject=company.id, role="company")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "company": self.format_company(company),
        }

    def list_employees(self, company_id: str) -> List[Dict[str, Any]]:
        employees = self.employee_repo.list_by_company(company_id, active_only=True)
        return [self.format_employee(e) for e in employees]

    def create_employee(self, company_id: str, emp_in: CompanyEmployeeCreate) -> Dict[str, Any]:
        clean_cpf = re.sub(r"\D", "", emp_in.cpf)
        employee = CompanyEmployee(
            company_id=company_id,
            full_name=emp_in.fullName.strip(),
            cpf=clean_cpf,
            email=emp_in.email.strip().lower(),
            phone=emp_in.phone,
            cost_center=emp_in.costCenter,
            department=emp_in.department,
            is_active=True,
        )
        created = self.employee_repo.create(employee)
        return self.format_employee(created)

    def delete_employee(self, company_id: str, employee_id: str) -> None:
        employee = self.employee_repo.get_by_id(employee_id, company_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Colaborador não encontrado."
            )
        self.employee_repo.deactivate(employee)

    def list_cost_centers(self, company_id: str) -> List[str]:
        return self.employee_repo.list_cost_centers(company_id)

    def list_invoices(self, company_id: str) -> List[Dict[str, Any]]:
        invoices = self.invoice_repo.list_by_company(company_id)
        return [self.format_invoice(inv) for inv in invoices]

    def list_all_admin(self, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        companies = self.company_repo.list_all(status=status, search=search)
        return [self.format_company(c) for c in companies]

    def update_company_admin(self, company_id: str, approval_in: CompanyAdminApprovalRequest) -> Dict[str, Any]:
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa não localizada."
            )

        if approval_in.status is not None:
            company.status = approval_in.status
        if approval_in.corporateDiscountPercent is not None:
            company.corporate_discount_percent = approval_in.corporateDiscountPercent
        if approval_in.creditLimit is not None:
            company.credit_limit = approval_in.creditLimit
        if approval_in.paymentTerms is not None:
            company.payment_terms = approval_in.paymentTerms

        updated = self.company_repo.update(company)
        return self.format_company(updated)

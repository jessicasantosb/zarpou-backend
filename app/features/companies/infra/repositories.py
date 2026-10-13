from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.companies.infra.models import Company, CompanyEmployee, CompanyInvoice


class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, company_id: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.id == company_id).first()

    def get_by_cnpj(self, cnpj: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.cnpj == cnpj).first()

    def get_by_email(self, email: str) -> Optional[Company]:
        return self.db.query(Company).filter(Company.corporate_email == email).first()

    def get_by_login(self, login_clean: str, login_digits: str) -> Optional[Company]:
        return self.db.query(Company).filter(
            (Company.corporate_email == login_clean) | (Company.cnpj == login_digits)
        ).first()

    def list_all(self, status: Optional[str] = None, search: Optional[str] = None) -> List[Company]:
        query = self.db.query(Company)
        if status:
            query = query.filter(Company.status == status)
        companies = query.order_by(Company.created_at.desc()).all()
        if search:
            term = search.strip().lower()
            companies = [
                c for c in companies
                if term in c.cnpj.lower()
                or term in c.razao_social.lower()
                or term in c.nome_fantasia.lower()
                or term in c.corporate_email.lower()
            ]
        return companies

    def create(self, company: Company) -> Company:
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def update(self, company: Company) -> Company:
        self.db.commit()
        self.db.refresh(company)
        return company


class CompanyEmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_company(self, company_id: str, active_only: bool = True) -> List[CompanyEmployee]:
        query = self.db.query(CompanyEmployee).filter(CompanyEmployee.company_id == company_id)
        if active_only:
            query = query.filter(CompanyEmployee.is_active == True)
        return query.all()

    def get_by_id(self, employee_id: str, company_id: str) -> Optional[CompanyEmployee]:
        return self.db.query(CompanyEmployee).filter(
            CompanyEmployee.id == employee_id,
            CompanyEmployee.company_id == company_id
        ).first()

    def create(self, employee: CompanyEmployee) -> CompanyEmployee:
        self.db.add(employee)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def deactivate(self, employee: CompanyEmployee) -> None:
        employee.is_active = False
        self.db.commit()

    def list_cost_centers(self, company_id: str) -> List[str]:
        employees = self.db.query(CompanyEmployee).filter(
            CompanyEmployee.company_id == company_id,
            CompanyEmployee.cost_center != None
        ).all()
        return sorted(list(set(e.cost_center for e in employees if e.cost_center)))


class CompanyInvoiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_company(self, company_id: str) -> List[CompanyInvoice]:
        return (
            self.db.query(CompanyInvoice)
            .filter(CompanyInvoice.company_id == company_id)
            .order_by(CompanyInvoice.created_at.desc())
            .all()
        )

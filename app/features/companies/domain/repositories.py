from typing import List, Optional, Protocol
from app.features.companies.domain.entities import CompanyEntity, CompanyEmployeeEntity, CompanyInvoiceEntity


class ICompanyRepository(Protocol):
    def get_by_id(self, company_id: str) -> Optional[CompanyEntity]:
        ...

    def get_by_cnpj(self, cnpj: str) -> Optional[CompanyEntity]:
        ...

    def get_by_email(self, email: str) -> Optional[CompanyEntity]:
        ...

    def list_all(self, status: Optional[str] = None, search: Optional[str] = None) -> List[CompanyEntity]:
        ...

    def save(self, company: CompanyEntity) -> CompanyEntity:
        ...


class ICompanyEmployeeRepository(Protocol):
    def list_by_company(self, company_id: str, active_only: bool = True) -> List[CompanyEmployeeEntity]:
        ...

    def get_by_id(self, employee_id: str, company_id: str) -> Optional[CompanyEmployeeEntity]:
        ...

    def save(self, employee: CompanyEmployeeEntity) -> CompanyEmployeeEntity:
        ...

    def deactivate(self, employee_id: str, company_id: str) -> bool:
        ...

    def list_cost_centers(self, company_id: str) -> List[str]:
        ...


class ICompanyInvoiceRepository(Protocol):
    def list_by_company(self, company_id: str) -> List[CompanyInvoiceEntity]:
        ...

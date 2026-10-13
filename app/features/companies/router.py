from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.api.deps import (
    get_db,
    get_current_admin_user,
    get_current_company_user,
    require_screen,
)
from app.features.users.infra.models import User
from app.features.companies.infra.models import Company
from app.features.companies.app.schemas import (
    CompanyRegisterRequest,
    CompanyLoginRequest,
    CompanyResponse,
    CompanyTokenResponse,
    CompanyEmployeeCreate,
    CompanyEmployeeResponse,
    CompanyInvoiceResponse,
    CompanyAdminApprovalRequest,
)
from app.features.companies.app.services import CompanyService

router = APIRouter()


@router.post("/register", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def register_company(
    reg_in: CompanyRegisterRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Cadastro inicial de nova empresa conveniada para Zarpou Empresas (B2B)."""
    service = CompanyService(db)
    return service.register(reg_in)


@router.post("/login", response_model=CompanyTokenResponse)
@limiter.limit("5/minute")
def login_company(
    request: Request,
    login_in: CompanyLoginRequest,
    db: Session = Depends(get_db)
) -> Any:
    """Autenticação do gestor corporativo com CNPJ ou E-mail corporativo + Senha."""
    service = CompanyService(db)
    return service.login(login_in)


@router.get("/me", response_model=CompanyResponse)
def get_company_me(
    company: Company = Depends(get_current_company_user)
) -> Any:
    """Retorna o perfil corporativo, limites de crédito disponíveis e termos de faturamento."""
    return CompanyService.format_company(company)


@router.get("/employees", response_model=List[CompanyEmployeeResponse])
@router.get("/me/employees", response_model=List[CompanyEmployeeResponse])
def list_company_employees(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company_user),
) -> Any:
    """Lista todos os colaboradores cadastrados para viagens a negócios da empresa."""
    service = CompanyService(db)
    return service.list_employees(company.id)


@router.post("/employees", response_model=CompanyEmployeeResponse, status_code=status.HTTP_201_CREATED)
@router.post("/me/employees", response_model=CompanyEmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_company_employee(
    emp_in: CompanyEmployeeCreate,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company_user),
) -> Any:
    """Cadastra um novo colaborador corporativo para emissão de passagens em 1 clique."""
    service = CompanyService(db)
    return service.create_employee(company.id, emp_in)


@router.delete("/employees/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_employee(
    id: str,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company_user),
) -> None:
    service = CompanyService(db)
    service.delete_employee(company.id, id)


@router.get("/cost-centers", response_model=List[str])
def list_company_cost_centers(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company_user),
) -> Any:
    """Lista de centros de custo cadastrados pelos colaboradores da empresa."""
    service = CompanyService(db)
    return service.list_cost_centers(company.id)


@router.get("/invoices", response_model=List[CompanyInvoiceResponse])
def list_company_invoices(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company_user),
) -> Any:
    """Extrato de faturamento quinzenal/mensal com download de boleto corporativo consolidado."""
    service = CompanyService(db)
    return service.list_invoices(company.id)


# ------------------------------------------------------------------------------
# ENDPOINTS ADMINISTRATIVOS (BACKOFFICE ZARPOU)
# ------------------------------------------------------------------------------

@router.get("/admin", response_model=List[CompanyResponse])
@router.get("/admin/all", response_model=List[CompanyResponse])
def list_all_companies(
    status_filter: Optional[str] = Query(None, description="Filtro por status: pendente, aprovada, bloqueada"),
    search: Optional[str] = Query(None, description="Busca por CNPJ ou Razão Social"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("usuarios")),
) -> Any:
    """Listagem de todas as empresas conveniadas para análise pelo time da Zarpou (Requer Admin)."""
    service = CompanyService(db)
    return service.list_all_admin(status=status_filter, search=search)


@router.patch("/admin/{id}", response_model=CompanyResponse)
@router.put("/admin/{id}", response_model=CompanyResponse)
@router.put("/{id}/approval", response_model=CompanyResponse)
def update_company_status_and_credit(
    id: str,
    approval_in: CompanyAdminApprovalRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("usuarios")),
) -> Any:
    """Aprovação de crédito corporativo, limite liberado e percentual de desconto PJ (Requer Admin)."""
    service = CompanyService(db)
    return service.update_company_admin(id, approval_in)

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen, get_current_customer_user, oauth2_scheme
from app.core.limiter import limiter
from app.core.token_revocation import revoke_token
from app.features.customers.infra.models import Customer
from app.features.customers.app.schemas import (
    CustomerAdminCreate,
    CustomerAdminUpdate,
    CustomerStatusUpdate,
    CustomerResponse,
    CustomerConsentUpdate,
    CustomerDeleteRequest,
)
from app.features.customers.app.services import CustomerService

router = APIRouter()


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    q: Optional[str] = Query(None, description="Busca por nome, e-mail, telefone ou CPF"),
    is_active: Optional[bool] = Query(None, description="Filtrar por status ativo/inativo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Lista todos os usuários / clientes viajantes da Zarpou.
    Acesso restrito a administradores com permissão de tela 'usuarios'.
    """
    service = CustomerService(db)
    return service.list_customers(q=q, is_active=is_active, skip=skip, limit=limit)


# ----------------------------------------------------------------------
# LGPD - Direitos do titular (cliente autenticado). Declaradas antes de /{id}.
# ----------------------------------------------------------------------

@router.get("/me/consent")
def get_my_consent(customer: Customer = Depends(get_current_customer_user)) -> Any:
    """Consulta o consentimento registrado (Política de Privacidade, Termos e marketing)."""
    return {"consent": customer.consent, "notifications": customer.notifications}


@router.post("/me/consent")
def record_my_consent(
    request: Request,
    consent_in: CustomerConsentUpdate,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """Registra/atualiza o consentimento LGPD com data, versão e IP de origem (prova do aceite)."""
    service = CustomerService(db)
    ip = request.client.host if request.client else None
    return service.record_consent(customer, consent_in, ip)


@router.get("/me/export-data")
@limiter.limit("5/hour")
def export_my_data(
    request: Request,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """Portabilidade (LGPD Art. 18 II e V): exporta todos os dados pessoais em JSON."""
    service = CustomerService(db)
    data = service.export_personal_data(customer)
    return JSONResponse(
        content=jsonable_encoder(data),
        headers={"Content-Disposition": f'attachment; filename="zarpou-meus-dados-{customer.id}.json"'},
    )


@router.delete("/me")
def delete_my_account(
    delete_in: CustomerDeleteRequest,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """
    Exclusão da conta (LGPD Art. 18 VI): anonimiza dados pessoais, preserva registros
    fiscais das reservas e encerra imediatamente a sessão atual.
    """
    service = CustomerService(db)
    result = service.anonymize_customer(customer, delete_in)
    if token:
        revoke_token(db, token)
    return result


@router.get("/{id}")
def get_customer_details(
    id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Retorna os detalhes completos do cliente e o histórico de suas reservas.
    """
    service = CustomerService(db)
    return service.get_customer_details(id)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer_in: CustomerAdminCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Cadastra um novo cliente manualmente pelo painel administrativo.
    """
    service = CustomerService(db)
    return service.create_customer(customer_in)


@router.put("/{id}", response_model=CustomerResponse)
def update_customer(
    id: str,
    customer_in: CustomerAdminUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Atualiza dados cadastrais de um cliente.
    """
    service = CustomerService(db)
    return service.update_customer(id, customer_in)


@router.patch("/{id}/status", response_model=CustomerResponse)
def toggle_customer_status(
    id: str,
    status_in: CustomerStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Ativa ou desativa a conta de um cliente.
    """
    service = CustomerService(db)
    return service.toggle_status(id, status_in)


@router.delete("/{id}")
def delete_customer(
    id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_screen("usuarios")),
) -> Any:
    """
    Remove um cliente e desvincula suas reservas.
    """
    service = CustomerService(db)
    return service.delete_customer(id)

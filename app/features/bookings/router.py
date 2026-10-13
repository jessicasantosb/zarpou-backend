from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_admin_user,
    get_optional_customer_user,
    get_current_customer_user,
    get_optional_company_user,
    require_screen,
    get_current_user_payload,
)
from app.features.customers.infra.models import Customer
from app.features.companies.infra.models import Company
from app.features.users.infra.models import User
from app.features.bookings.app.schemas import (
    BookingCreate,
    BookingStatusUpdate,
    BookingResponse,
)
from app.features.bookings.app.services import BookingService

router = APIRouter()


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
@router.post("/checkout", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreate,
    db: Session = Depends(get_db),
    customer: Optional[Customer] = Depends(get_optional_customer_user),
    company: Optional[Company] = Depends(get_optional_company_user),
) -> Any:
    """Criação e emissão de reserva (B2C e B2B Corporativo) com cálculo de valores e localizador PNR."""
    service = BookingService(db)
    return service.create(booking_in, customer=customer, company=company)


@router.get("/my-trips", response_model=List[BookingResponse])
@router.get("/my", response_model=List[BookingResponse])
def get_my_trips(
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_current_customer_user),
) -> Any:
    """Lista de todas as viagens e vouchers do cliente autenticado."""
    service = BookingService(db)
    return service.get_my_trips(customer.id)


@router.get("/locator/{locator_code}", response_model=BookingResponse)
def get_booking_by_locator(
    locator_code: str,
    email: Optional[str] = Query(None, description="E-mail do titular (obrigatório para consultas sem login)"),
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload),
) -> Any:
    """Consulta rápida de voucher por código localizador (PNR). Exige login do titular ou e-mail."""
    service = BookingService(db)
    return service.get_by_locator(locator_code, email=email, payload=payload)


@router.get("", response_model=List[BookingResponse])
def list_all_bookings(
    search: Optional[str] = Query(None, description="Busca por localizador, nome ou cidade"),
    status_filter: Optional[str] = Query(None, description="Filtro de status"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("reservas")),
) -> Any:
    """Gestão administrativa completa de pedidos e reservas emitidas (Requer Admin)."""
    service = BookingService(db)
    return service.list_all(status=status_filter, search=search)


@router.get("/{id_or_locator}", response_model=BookingResponse)
def get_booking_unified(
    id_or_locator: str,
    email: Optional[str] = Query(None, description="E-mail do titular (obrigatório para consultas sem login)"),
    db: Session = Depends(get_db),
    payload: Optional[dict] = Depends(get_current_user_payload),
) -> Any:
    """Consulta unificada de reserva por ID interno ou PNR. Exige login do titular ou e-mail."""
    service = BookingService(db)
    return service.get_unified(id_or_locator, email=email, payload=payload)


@router.patch("/{id}/status", response_model=BookingResponse)
def update_booking_status(
    id: str,
    status_in: BookingStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("reservas")),
) -> Any:
    """Atualizar status da reserva pelo painel administrativo."""
    service = BookingService(db)
    return service.update_status(id, status_in)

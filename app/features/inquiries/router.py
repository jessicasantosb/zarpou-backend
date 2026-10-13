from typing import Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.inquiries.app.schemas import (
    InquiryCreate,
    InquiryStatusUpdate,
    InquiryResponse,
)
from app.features.inquiries.app.services import InquiryService

router = APIRouter()


@router.post("", response_model=InquiryResponse, status_code=status.HTTP_201_CREATED)
def create_inquiry(
    inquiry_in: InquiryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Any:
    """Submissão do formulário de consultoria de viagens personalizada."""
    service = InquiryService(db)
    return service.create(inquiry_in, background_tasks=background_tasks)


@router.get("", response_model=List[InquiryResponse])
def list_inquiries(
    status_filter: Optional[str] = Query(None, description="Filtro de status do lead"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("dashboard")),
) -> Any:
    """Listagem de leads e solicitações de consultoria (Requer Admin)."""
    service = InquiryService(db)
    return service.list(status=status_filter)


@router.patch("/{id}/status", response_model=InquiryResponse)
def update_inquiry_status(
    id: str,
    status_in: InquiryStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("dashboard")),
) -> Any:
    service = InquiryService(db)
    return service.update_status(id, status_in)

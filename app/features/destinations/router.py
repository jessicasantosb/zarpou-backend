from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.destinations.app.schemas import (
    DestinationCreate,
    DestinationUpdate,
    DestinationResponse,
)
from app.features.destinations.app.services import DestinationService

router = APIRouter()


@router.get("", response_model=List[DestinationResponse])
def list_destinations(
    category: Optional[str] = Query(None, description="Filtro por categoria: all, national, international"),
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Any:
    """Lista todos os destinos cadastrados (para carrossel da Home e filtros)."""
    service = DestinationService(db)
    return service.list(category=category, active_only=active_only)


@router.get("/{id}", response_model=DestinationResponse)
def get_destination(
    id: str,
    db: Session = Depends(get_db),
) -> Any:
    service = DestinationService(db)
    return service.get_by_id(id)


@router.post("", response_model=DestinationResponse, status_code=status.HTTP_201_CREATED)
def create_destination(
    destination_in: DestinationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("destinos")),
) -> Any:
    """Criar novo destino no catálogo (Requer Admin)."""
    service = DestinationService(db)
    return service.create(destination_in)


@router.put("/{id}", response_model=DestinationResponse)
def update_destination(
    id: str,
    destination_in: DestinationUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("destinos")),
) -> Any:
    service = DestinationService(db)
    return service.update(id, destination_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_destination(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("destinos")),
) -> None:
    service = DestinationService(db)
    service.delete(id)

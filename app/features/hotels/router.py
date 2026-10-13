from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.hotels.app.schemas import (
    HotelCreate,
    HotelUpdate,
    HotelResponse,
    RoomCreate,
    RoomResponse,
)
from app.features.hotels.app.services import HotelService

router = APIRouter()


@router.get("", response_model=List[HotelResponse])
def list_hotels(
    city: Optional[str] = Query(None, description="Filtro por cidade ou destino"),
    stars: Optional[int] = Query(None, description="Filtro por número de estrelas (1-5)"),
    min_price: Optional[float] = Query(None, description="Preço mínimo por diária"),
    max_price: Optional[float] = Query(None, description="Preço máximo por diária"),
    featured_only: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Any:
    """Lista de hotéis com filtros de busca completos para a página /hospedagens e Home."""
    service = HotelService(db)
    return service.list(
        city=city,
        stars=stars,
        min_price=min_price,
        max_price=max_price,
        featured_only=featured_only,
        active_only=active_only,
    )


@router.get("/{id}", response_model=HotelResponse)
def get_hotel(
    id: str,
    db: Session = Depends(get_db),
) -> Any:
    service = HotelService(db)
    return service.get_by_id(id)


@router.post("", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
def create_hotel(
    hotel_in: HotelCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("hospedagens")),
) -> Any:
    """Criar novo hotel com seus quartos (Requer Admin)."""
    service = HotelService(db)
    return service.create(hotel_in)


@router.put("/{id}", response_model=HotelResponse)
def update_hotel(
    id: str,
    hotel_in: HotelUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("hospedagens")),
) -> Any:
    service = HotelService(db)
    return service.update(id, hotel_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hotel(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("hospedagens")),
) -> None:
    service = HotelService(db)
    service.delete(id)


@router.post("/{hotel_id}/rooms", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    hotel_id: str,
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("hospedagens")),
) -> Any:
    service = HotelService(db)
    return service.add_room(hotel_id, room_in)

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.flights.app.schemas import (
    FlightCreate,
    FlightUpdate,
    FlightResponse,
)
from app.features.flights.app.services import FlightService

router = APIRouter()


@router.get("", response_model=List[FlightResponse])
def list_flights(
    origin_iata: Optional[str] = Query(None, description="Aeroporto de origem (ex: CNF, GRU)"),
    destination_iata: Optional[str] = Query(None, description="Aeroporto de destino (ex: MIA, FCO)"),
    region: Optional[str] = Query(None, description="Região: all, usa, europe, south-america, other"),
    featured_only: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Any:
    """Lista de voos e passagens aéreas com filtros para a página /passagens e Home."""
    service = FlightService(db)
    return service.list(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        region=region,
        featured_only=featured_only,
        active_only=active_only,
    )


@router.get("/{id}", response_model=FlightResponse)
def get_flight(
    id: str,
    db: Session = Depends(get_db),
) -> Any:
    service = FlightService(db)
    return service.get_by_id(id)


@router.post("", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
def create_flight(
    flight_in: FlightCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("passagens")),
) -> Any:
    """Cadastrar nova passagem aérea com trechos de ida e opcional volta (Requer Admin)."""
    service = FlightService(db)
    return service.create(flight_in)


@router.put("/{id}", response_model=FlightResponse)
def update_flight(
    id: str,
    flight_in: FlightUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("passagens")),
) -> Any:
    service = FlightService(db)
    return service.update(id, flight_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flight(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("passagens")),
) -> None:
    service = FlightService(db)
    service.delete(id)

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.features.flights.infra.models import Flight, FlightSegment
from app.features.flights.infra.repositories import FlightRepository
from app.features.flights.app.schemas import FlightCreate, FlightUpdate


class FlightService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FlightRepository(db)

    def list(
        self,
        origin_iata: Optional[str] = None,
        destination_iata: Optional[str] = None,
        region: Optional[str] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[Flight]:
        return self.repo.list(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            region=region,
            featured_only=featured_only,
            active_only=active_only,
        )

    def get_by_id(self, flight_id: str) -> Flight:
        flight = self.repo.get_by_id(flight_id)
        if not flight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voo não encontrado."
            )
        return flight

    def create(self, flight_in: FlightCreate) -> Flight:
        existing = self.repo.get_by_id(flight_in.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Voo com este ID já existe."
            )

        flight_data = flight_in.model_dump(exclude={"outbound", "return_flight"})
        flight = Flight(**flight_data)
        self.db.add(flight)
        self.db.flush()

        out_seg = FlightSegment(
            id=f"seg-{flight.id}-out",
            flight_id=flight.id,
            **flight_in.outbound.model_dump()
        )
        self.db.add(out_seg)

        if flight_in.return_flight:
            ret_seg = FlightSegment(
                id=f"seg-{flight.id}-ret",
                flight_id=flight.id,
                **flight_in.return_flight.model_dump()
            )
            self.db.add(ret_seg)

        self.db.commit()
        self.db.refresh(flight)
        return flight

    def update(self, flight_id: str, flight_in: FlightUpdate) -> Flight:
        flight = self.get_by_id(flight_id)
        update_data = flight_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(flight, field, val)
        return self.repo.update(flight)

    def delete(self, flight_id: str) -> None:
        flight = self.get_by_id(flight_id)
        self.repo.delete(flight)

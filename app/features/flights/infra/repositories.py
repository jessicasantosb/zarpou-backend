from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.flights.infra.models import Flight, FlightSegment


class FlightRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        origin_iata: Optional[str] = None,
        destination_iata: Optional[str] = None,
        region: Optional[str] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[Flight]:
        query = self.db.query(Flight)
        if active_only:
            query = query.filter(Flight.is_active == True)
        if featured_only:
            query = query.filter(Flight.featured == True)
        if region and region != "all":
            query = query.filter(Flight.region == region)

        flights = query.all()
        if origin_iata or destination_iata:
            filtered = []
            for f in flights:
                match = False
                for s in f.segments:
                    if origin_iata and s.origin_iata.upper() != origin_iata.upper():
                        continue
                    if destination_iata and s.destination_iata.upper() != destination_iata.upper():
                        continue
                    match = True
                    break
                if match:
                    filtered.append(f)
            return filtered

        return flights

    def get_by_id(self, flight_id: str) -> Optional[Flight]:
        return self.db.query(Flight).filter(Flight.id == flight_id).first()

    def create(self, flight: Flight) -> Flight:
        self.db.add(flight)
        self.db.commit()
        self.db.refresh(flight)
        return flight

    def update(self, flight: Flight) -> Flight:
        self.db.commit()
        self.db.refresh(flight)
        return flight

    def delete(self, flight: Flight) -> None:
        self.db.delete(flight)
        self.db.commit()

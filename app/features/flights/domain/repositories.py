from typing import List, Optional, Protocol
from app.features.flights.domain.entities import FlightEntity, FlightSegmentEntity


class IFlightRepository(Protocol):
    def list(
        self,
        origin_iata: Optional[str] = None,
        destination_iata: Optional[str] = None,
        region: Optional[str] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[FlightEntity]:
        ...

    def get_by_id(self, flight_id: str) -> Optional[FlightEntity]:
        ...

    def save(self, flight: FlightEntity) -> FlightEntity:
        ...

    def delete(self, flight_id: str) -> bool:
        ...

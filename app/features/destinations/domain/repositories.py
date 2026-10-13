from typing import List, Optional, Protocol
from app.features.destinations.domain.entities import DestinationEntity


class IDestinationRepository(Protocol):
    def list(self, category: Optional[str] = None, active_only: bool = True) -> List[DestinationEntity]:
        ...

    def get_by_id(self, destination_id: str) -> Optional[DestinationEntity]:
        ...

    def save(self, destination: DestinationEntity) -> DestinationEntity:
        ...

    def delete(self, destination_id: str) -> bool:
        ...

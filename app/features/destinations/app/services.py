from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.features.destinations.infra.models import Destination
from app.features.destinations.infra.repositories import DestinationRepository
from app.features.destinations.app.schemas import DestinationCreate, DestinationUpdate


class DestinationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DestinationRepository(db)

    def list(self, category: Optional[str] = None, active_only: bool = True) -> List[Destination]:
        return self.repo.list(category=category, active_only=active_only)

    def get_by_id(self, destination_id: str) -> Destination:
        destination = self.repo.get_by_id(destination_id)
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Destino não encontrado."
            )
        return destination

    def create(self, destination_in: DestinationCreate) -> Destination:
        existing = self.repo.get_by_id(destination_in.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destino com este ID já existe."
            )

        destination = Destination(**destination_in.model_dump())
        return self.repo.create(destination)

    def update(self, destination_id: str, destination_in: DestinationUpdate) -> Destination:
        destination = self.get_by_id(destination_id)
        update_data = destination_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(destination, field, val)
        return self.repo.update(destination)

    def delete(self, destination_id: str) -> None:
        destination = self.get_by_id(destination_id)
        self.repo.delete(destination)

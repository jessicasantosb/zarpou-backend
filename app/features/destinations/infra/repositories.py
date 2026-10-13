from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.destinations.infra.models import Destination


class DestinationRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, category: Optional[str] = None, active_only: bool = True) -> List[Destination]:
        query = self.db.query(Destination)
        if active_only:
            query = query.filter(Destination.is_active == True)
        if category and category != "all":
            query = query.filter(Destination.category == category)
        return query.order_by(Destination.display_order.asc()).all()

    def get_by_id(self, destination_id: str) -> Optional[Destination]:
        return self.db.query(Destination).filter(Destination.id == destination_id).first()

    def create(self, destination: Destination) -> Destination:
        self.db.add(destination)
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def update(self, destination: Destination) -> Destination:
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def delete(self, destination: Destination) -> None:
        self.db.delete(destination)
        self.db.commit()

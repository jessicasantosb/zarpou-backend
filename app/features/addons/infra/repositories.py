from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.addons.infra.models import Addon


class SqlAlchemyAddonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self) -> List[Addon]:
        return self.db.query(Addon).filter(Addon.is_active == True).all()

    def get_by_id(self, addon_id: str) -> Optional[Addon]:
        return self.db.query(Addon).filter(Addon.id == addon_id).first()

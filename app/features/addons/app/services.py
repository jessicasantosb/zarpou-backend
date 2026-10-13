from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.addons.infra.repositories import SqlAlchemyAddonRepository
from app.features.addons.infra.models import Addon


class AddonService:
    def __init__(self, db: Session):
        self.repository = SqlAlchemyAddonRepository(db)

    def list_active_addons(self) -> List[Addon]:
        return self.repository.get_active()

    def get_addon_by_id(self, addon_id: str) -> Optional[Addon]:
        return self.repository.get_by_id(addon_id)

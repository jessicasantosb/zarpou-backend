from typing import List, Optional, Protocol
from app.features.addons.domain.entities import AddonEntity


class AddonRepository(Protocol):
    def get_active(self) -> List[AddonEntity]:
        ...

    def get_by_id(self, addon_id: str) -> Optional[AddonEntity]:
        ...

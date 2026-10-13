from typing import List, Optional, Protocol
from app.features.promotions.domain.entities import PromotionEntity


class IPromotionRepository(Protocol):
    def list(self, active_only: bool = True) -> List[PromotionEntity]:
        ...

    def get_by_id(self, promotion_id: str) -> Optional[PromotionEntity]:
        ...

    def save(self, promotion: PromotionEntity) -> PromotionEntity:
        ...

    def delete(self, promotion_id: str) -> bool:
        ...

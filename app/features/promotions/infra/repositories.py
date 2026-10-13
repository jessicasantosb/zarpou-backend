from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.promotions.infra.models import Promotion


class PromotionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, active_only: bool = True) -> List[Promotion]:
        query = self.db.query(Promotion)
        if active_only:
            query = query.filter(Promotion.active == True)
        return query.order_by(Promotion.display_order.asc()).all()

    def get_by_id(self, promo_id: str) -> Optional[Promotion]:
        return self.db.query(Promotion).filter(Promotion.id == promo_id).first()

    def create(self, promo: Promotion) -> Promotion:
        self.db.add(promo)
        self.db.commit()
        self.db.refresh(promo)
        return promo

    def update(self, promo: Promotion) -> Promotion:
        self.db.commit()
        self.db.refresh(promo)
        return promo

    def delete(self, promo: Promotion) -> None:
        self.db.delete(promo)
        self.db.commit()

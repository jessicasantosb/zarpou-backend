from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.coupons.infra.models import Coupon


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, active_only: bool = False, search: Optional[str] = None) -> List[Coupon]:
        query = self.db.query(Coupon)
        if active_only:
            query = query.filter(Coupon.active == True)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(Coupon.code.ilike(term) | Coupon.description.ilike(term))
        return query.order_by(Coupon.created_at.desc()).all()

    def get_by_id(self, coupon_id: str) -> Optional[Coupon]:
        return self.db.query(Coupon).filter(Coupon.id == coupon_id).first()

    def get_by_code(self, code: str) -> Optional[Coupon]:
        return self.db.query(Coupon).filter(Coupon.code == code.upper()).first()

    def create(self, coupon: Coupon) -> Coupon:
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def update(self, coupon: Coupon) -> Coupon:
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def delete(self, coupon: Coupon) -> None:
        self.db.delete(coupon)
        self.db.commit()

from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.bookings.infra.models import Booking


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, booking_id: str) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.id == booking_id).first()

    def get_by_locator(self, locator_code: str) -> Optional[Booking]:
        return self.db.query(Booking).filter(Booking.locator_code == locator_code).first()

    def get_by_id_or_locator(self, query: str) -> Optional[Booking]:
        return (
            self.db.query(Booking)
            .filter((Booking.id == query) | (Booking.locator_code == query.upper()))
            .first()
        )

    def list_by_customer(self, customer_id: str) -> List[Booking]:
        return (
            self.db.query(Booking)
            .filter(Booking.customer_id == customer_id)
            .order_by(Booking.created_at.desc())
            .all()
        )

    def list_all(self, status: Optional[str] = None, search: Optional[str] = None) -> List[Booking]:
        query = self.db.query(Booking)
        if status and status != "todos":
            query = query.filter(Booking.status == status)

        bookings = query.order_by(Booking.created_at.desc()).all()
        if search:
            term = search.strip().lower()
            filtered = []
            for b in bookings:
                if term in b.locator_code.lower():
                    filtered.append(b)
                elif any(term in (t.full_name or "").lower() for t in b.travelers):
                    filtered.append(b)
                elif b.hotel and term in b.hotel.name.lower():
                    filtered.append(b)
            return filtered

        return bookings

    def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def update(self, booking: Booking) -> Booking:
        self.db.commit()
        self.db.refresh(booking)
        return booking

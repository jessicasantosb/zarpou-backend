from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.hotels.infra.models import Hotel, Room


class HotelRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        city: Optional[str] = None,
        stars: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[Hotel]:
        query = self.db.query(Hotel)
        if active_only:
            query = query.filter(Hotel.is_active == True)
        if featured_only:
            query = query.filter(Hotel.featured == True)
        if city:
            query = query.filter(Hotel.city.ilike(f"%{city.strip()}%"))
        if stars:
            query = query.filter(Hotel.stars >= stars)
        if min_price is not None:
            query = query.filter(Hotel.base_price_per_night >= min_price)
        if max_price is not None:
            query = query.filter(Hotel.base_price_per_night <= max_price)
        return query.all()

    def get_by_id(self, hotel_id: str) -> Optional[Hotel]:
        return self.db.query(Hotel).filter(Hotel.id == hotel_id).first()

    def create(self, hotel: Hotel) -> Hotel:
        self.db.add(hotel)
        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def update(self, hotel: Hotel) -> Hotel:
        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def delete(self, hotel: Hotel) -> None:
        self.db.delete(hotel)
        self.db.commit()


class RoomRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, room_id: str) -> Optional[Room]:
        return self.db.query(Room).filter(Room.id == room_id).first()

    def create(self, room: Room) -> Room:
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

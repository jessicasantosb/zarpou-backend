from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.features.hotels.infra.models import Hotel, Room
from app.features.hotels.infra.repositories import HotelRepository, RoomRepository
from app.features.hotels.app.schemas import HotelCreate, HotelUpdate, RoomCreate


class HotelService:
    def __init__(self, db: Session):
        self.db = db
        self.hotel_repo = HotelRepository(db)
        self.room_repo = RoomRepository(db)

    def list(
        self,
        city: Optional[str] = None,
        stars: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[Hotel]:
        return self.hotel_repo.list(
            city=city,
            stars=stars,
            min_price=min_price,
            max_price=max_price,
            featured_only=featured_only,
            active_only=active_only,
        )

    def get_by_id(self, hotel_id: str) -> Hotel:
        hotel = self.hotel_repo.get_by_id(hotel_id)
        if not hotel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hotel não encontrado."
            )
        return hotel

    def create(self, hotel_in: HotelCreate) -> Hotel:
        existing = self.hotel_repo.get_by_id(hotel_in.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hotel com este ID já existe."
            )

        hotel_data = hotel_in.model_dump(exclude={"rooms"})
        hotel = Hotel(**hotel_data)
        self.db.add(hotel)
        self.db.flush()

        if hotel_in.rooms:
            for idx, room_data in enumerate(hotel_in.rooms):
                room_id = f"room-{hotel.id}-{idx + 1}"
                room = Room(id=room_id, hotel_id=hotel.id, **room_data.model_dump())
                self.db.add(room)

        self.db.commit()
        self.db.refresh(hotel)
        return hotel

    def update(self, hotel_id: str, hotel_in: HotelUpdate) -> Hotel:
        hotel = self.get_by_id(hotel_id)
        update_data = hotel_in.model_dump(exclude_unset=True)
        for field, val in update_data.items():
            setattr(hotel, field, val)
        return self.hotel_repo.update(hotel)

    def delete(self, hotel_id: str) -> None:
        hotel = self.get_by_id(hotel_id)
        self.hotel_repo.delete(hotel)

    def add_room(self, hotel_id: str, room_in: RoomCreate) -> Room:
        self.get_by_id(hotel_id)  # Validate hotel exists
        room = Room(**room_in.model_dump())
        return self.room_repo.create(room)

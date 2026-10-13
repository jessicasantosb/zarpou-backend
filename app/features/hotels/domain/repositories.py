from typing import List, Optional, Protocol
from app.features.hotels.domain.entities import HotelEntity, RoomEntity


class IHotelRepository(Protocol):
    def list(
        self,
        city: Optional[str] = None,
        stars: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        featured_only: bool = False,
        active_only: bool = True,
    ) -> List[HotelEntity]:
        ...

    def get_by_id(self, hotel_id: str) -> Optional[HotelEntity]:
        ...

    def save(self, hotel: HotelEntity) -> HotelEntity:
        ...

    def delete(self, hotel_id: str) -> bool:
        ...


class IRoomRepository(Protocol):
    def get_by_id(self, room_id: str) -> Optional[RoomEntity]:
        ...

    def save(self, room: RoomEntity) -> RoomEntity:
        ...

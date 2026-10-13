from typing import List, Optional, Protocol
from app.features.bookings.domain.entities import BookingEntity


class IBookingRepository(Protocol):
    def get_by_id(self, booking_id: str) -> Optional[BookingEntity]:
        ...

    def get_by_locator(self, locator_code: str) -> Optional[BookingEntity]:
        ...

    def list_by_customer(self, customer_id: str) -> List[BookingEntity]:
        ...

    def list_all(self, status: Optional[str] = None, search: Optional[str] = None) -> List[BookingEntity]:
        ...

    def save(self, booking: BookingEntity) -> BookingEntity:
        ...

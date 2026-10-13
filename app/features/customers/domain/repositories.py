from typing import List, Optional, Protocol
from app.features.customers.domain.entities import CustomerEntity


class CustomerRepository(Protocol):
    def get_by_id(self, customer_id: str) -> Optional[CustomerEntity]:
        ...

    def get_by_email(self, email: str) -> Optional[CustomerEntity]:
        ...

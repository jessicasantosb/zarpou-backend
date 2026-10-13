from typing import List, Optional, Protocol
from app.features.users.domain.entities import UserEntity


class UserRepository(Protocol):
    def get_all(self) -> List[UserEntity]:
        ...

    def get_by_id(self, user_id: str) -> Optional[UserEntity]:
        ...

    def get_by_email(self, email: str) -> Optional[UserEntity]:
        ...

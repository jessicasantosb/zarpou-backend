from typing import List, Optional, Protocol
from app.features.chat.domain.entities import ChatLogEntity


class IChatLogRepository(Protocol):
    def get_history(self, session_id: str, limit: int = 60) -> List[ChatLogEntity]:
        ...

    def save_messages(self, logs: List[ChatLogEntity]) -> None:
        ...

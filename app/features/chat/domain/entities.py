from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChatLogEntity:
    id: str
    session_id: str
    role: str
    content: str
    customer_id: Optional[str] = None
    created_at: Optional[datetime] = None

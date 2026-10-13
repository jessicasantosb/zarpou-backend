from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from app.core.database import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(String(50), primary_key=True, default=lambda: f"chat-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(100), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def sessionId(self) -> str:
        return self.session_id

    @property
    def createdAt(self) -> datetime:
        return self.created_at

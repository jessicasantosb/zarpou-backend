from typing import Any, List, Optional
from sqlalchemy.orm import Session
from app.features.chat.infra.models import ChatLog


class ChatLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_history(self, session_id: str, limit: int = 60) -> List[ChatLog]:
        return (
            self.db.query(ChatLog)
            .filter(ChatLog.session_id == session_id)
            .order_by(ChatLog.created_at.asc())
            .limit(limit)
            .all()
        )

    def get_customer_history(
        self,
        customer_id: str,
        session_id: Optional[str] = None,
        limit: int = 60,
    ) -> List[ChatLog]:
        """Histórico restrito às conversas do próprio cliente (proteção IDOR/LGPD)."""
        query = self.db.query(ChatLog).filter(ChatLog.customer_id == customer_id)
        if session_id:
            query = query.filter(ChatLog.session_id == session_id)
        return query.order_by(ChatLog.created_at.asc()).limit(limit).all()

    def save_messages(self, session_id: str, customer_id: Optional[str], user_msg: str, bot_reply: str) -> None:
        try:
            user_log = ChatLog(session_id=session_id, customer_id=customer_id, role="user", content=user_msg)
            bot_log = ChatLog(session_id=session_id, customer_id=customer_id, role="assistant", content=bot_reply)
            self.db.add_all([user_log, bot_log])
            self.db.commit()
        except Exception as e:
            print("Erro ao registrar log de chat:", e)

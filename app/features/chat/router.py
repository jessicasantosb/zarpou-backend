from typing import Any, List
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_optional_customer_user
from app.core.limiter import limiter
from app.features.customers.infra.models import Customer
from app.features.chat.app.schemas import ChatRequest, ChatResponse, ChatLogResponse
from app.features.chat.app.services import ChatService

router = APIRouter()


@router.get("/history", response_model=List[ChatLogResponse])
def get_chat_history(
    sessionId: str = Query("default-session", description="Identificador da sessão do chat"),
    db: Session = Depends(get_db),
) -> Any:
    """Retorna o histórico de mensagens de uma sessão específica."""
    service = ChatService(db)
    return service.get_history(sessionId)


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_concierge(
    request: Request,
    req: ChatRequest,
    db: Session = Depends(get_db),
    customer: Customer = Depends(get_optional_customer_user),
) -> Any:
    """Concierge Virtual da Zarpou Viagens e Turismo."""
    service = ChatService(db)
    return await service.chat(req, customer.id if customer else None)

from typing import Any, List
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.promotions.app.schemas import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
)
from app.features.promotions.app.services import PromotionService

router = APIRouter()


@router.get("", response_model=List[PromotionResponse])
def list_promotions(
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Any:
    """Lista de promoções ativas para os cards promocionais na Home e Admin."""
    service = PromotionService(db)
    return service.list(active_only=active_only)


@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
def create_promotion(
    promo_in: PromotionCreate,
    background_tasks: BackgroundTasks,
    notify_subscribers: bool = True,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("promocoes")),
) -> Any:
    """Cria nova promoção no painel e dispara notificações aos clientes inscritos."""
    service = PromotionService(db)
    return service.create(promo_in, background_tasks=background_tasks, notify_subscribers=notify_subscribers)


@router.put("/{id}", response_model=PromotionResponse)
def update_promotion(
    id: str,
    promo_in: PromotionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("promocoes")),
) -> Any:
    service = PromotionService(db)
    return service.update(id, promo_in)


@router.patch("/{id}/toggle", response_model=PromotionResponse)
def toggle_promotion(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("promocoes")),
) -> Any:
    service = PromotionService(db)
    return service.toggle(id)


@router.post("/{id}/notify", status_code=status.HTTP_200_OK)
def notify_promotion_subscribers(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("promocoes")),
) -> Any:
    """Dispara manualmente notificações da promoção para todos os clientes cadastrados."""
    service = PromotionService(db)
    return service.notify_subscribers(id, background_tasks=background_tasks)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_promotion(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("promocoes")),
) -> None:
    service = PromotionService(db)
    service.delete(id)

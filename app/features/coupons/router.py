from typing import Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_screen
from app.features.users.infra.models import User
from app.features.coupons.app.schemas import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    CouponGenerateRequest,
    CouponCodeResponse,
    CouponValidateRequest,
    CouponValidateResponse,
)
from app.features.coupons.app.services import CouponService

router = APIRouter()


@router.get("", response_model=List[CouponResponse])
def list_coupons(
    active_only: bool = False,
    search: Optional[str] = Query(None, description="Busca por código ou descrição do cupom"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Lista de cupons de desconto cadastrados no painel (Requer Admin)."""
    service = CouponService(db)
    return service.list(active_only=active_only, search=search)


@router.post("/generate-code", response_model=CouponCodeResponse)
def generate_coupon_code(
    payload: CouponGenerateRequest = CouponGenerateRequest(),
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Gera um código aleatório único, em maiúsculas, para novo cupom (Requer Admin)."""
    service = CouponService(db)
    return service.generate(prefix=payload.prefix, length=payload.length)


@router.post("/validate", response_model=CouponValidateResponse)
def validate_coupon(
    payload: CouponValidateRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Valida um cupom para o checkout do cliente (público). Retorna o desconto aplicável."""
    service = CouponService(db)
    coupon, discount_amount = service.validate_for_checkout(
        code=payload.code,
        order_amount=payload.order_amount,
        customer_email=payload.customer_email,
    )
    return CouponValidateResponse(
        valid=True,
        code=coupon.code,
        description=coupon.description,
        discount_type=coupon.discount_type,
        discount_value=float(coupon.discount_value),
        discount_amount=discount_amount,
        min_order_amount=float(coupon.min_order_amount) if coupon.min_order_amount is not None else None,
        valid_to=coupon.valid_to,
    )


@router.get("/{id}", response_model=CouponResponse)
def get_coupon(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Detalhes de um cupom específico (Requer Admin)."""
    service = CouponService(db)
    return service.get_by_id(id)


@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    coupon_in: CouponCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Cria novo cupom de desconto no painel (Requer Admin)."""
    service = CouponService(db)
    return service.create(coupon_in, created_by=admin.id)


@router.put("/{id}", response_model=CouponResponse)
def update_coupon(
    id: str,
    coupon_in: CouponUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Atualiza um cupom existente (Requer Admin)."""
    service = CouponService(db)
    return service.update(id, coupon_in)


@router.patch("/{id}/toggle", response_model=CouponResponse)
def toggle_coupon(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Ativa ou desativa um cupom (Requer Admin)."""
    service = CouponService(db)
    return service.toggle(id)


@router.post("/{id}/notify", status_code=status.HTTP_200_OK)
def notify_coupon_subscribers(
    id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> Any:
    """Dispara a notificação do cupom (e-mail + WhatsApp) para clientes com opt-in (Requer Admin)."""
    service = CouponService(db)
    return service.notify(id, background_tasks=background_tasks, force=force)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("cupons")),
) -> None:
    """Remove um cupom do painel (Requer Admin)."""
    service = CouponService(db)
    service.delete(id)

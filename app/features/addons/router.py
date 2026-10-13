from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.features.addons.app.schemas import AddonResponse
from app.features.addons.app.services import AddonService

router = APIRouter()


@router.get("", response_model=List[AddonResponse])
def list_addons(
    db: Session = Depends(get_db)
) -> Any:
    """
    Lista de itens adicionais para a etapa de extras do checkout (seguro viagem, bagagem, transfer).
    """
    service = AddonService(db)
    return service.list_active_addons()

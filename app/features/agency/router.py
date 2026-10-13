from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.models.user import User
from app.features.agency.app.schemas import (
    AgencySettingSchema,
    HeroConfigSchema,
    DashboardMetrics,
)
from app.features.agency.app.services import AgencyService

router = APIRouter()


@router.get("/settings", response_model=AgencySettingSchema)
def get_agency_settings(
    db: Session = Depends(get_db)
) -> Any:
    service = AgencyService(db)
    return service.get_settings()


@router.put("/settings", response_model=AgencySettingSchema)
def update_agency_settings(
    data: AgencySettingSchema,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("configuracoes")),
) -> Any:
    """
    Atualiza as configurações gerais e as credenciais de integrações
    (Resend, WhatsApp, MercadoPago e IA) inseridas pelo frontend.
    """
    service = AgencyService(db)
    return service.update_settings(data)


@router.get("/hero", response_model=HeroConfigSchema)
def get_hero_config(
    db: Session = Depends(get_db)
) -> Any:
    service = AgencyService(db)
    return service.get_hero_config()


@router.put("/hero", response_model=HeroConfigSchema)
def update_hero_config(
    data: HeroConfigSchema,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("hero")),
) -> Any:
    service = AgencyService(db)
    return service.update_hero_config(data)


@router.get("/dashboard", response_model=DashboardMetrics)
@router.get("/metrics", response_model=DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("dashboard")),
) -> Any:
    """
    Métricas consolidadas para a tela de dashboard da agência (/admin/dashboard).
    """
    service = AgencyService(db)
    return service.get_dashboard_metrics()

from typing import Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin_user, require_screen
from app.features.users.infra.models import User
from app.features.packages.app.schemas import (
    PackageCreate,
    PackageResponse,
)
from app.features.packages.app.services import PackageService

router = APIRouter()


@router.get("", response_model=List[PackageResponse])
def list_packages(
    featured_only: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
) -> Any:
    service = PackageService(db)
    return service.list(featured_only=featured_only, active_only=active_only)


@router.get("/{id}", response_model=PackageResponse)
def get_package(
    id: str,
    db: Session = Depends(get_db),
) -> Any:
    service = PackageService(db)
    return service.get_by_id(id)


@router.post("", response_model=PackageResponse, status_code=status.HTTP_201_CREATED)
def create_package(
    package_in: PackageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("destinos")),
) -> Any:
    service = PackageService(db)
    return service.create(package_in)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_screen("destinos")),
) -> None:
    service = PackageService(db)
    service.delete(id)

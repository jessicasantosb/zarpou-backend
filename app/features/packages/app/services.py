from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.features.packages.infra.models import Package
from app.features.packages.infra.repositories import PackageRepository
from app.features.packages.app.schemas import PackageCreate


class PackageService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PackageRepository(db)

    def list(self, featured_only: bool = False, active_only: bool = True) -> List[Package]:
        return self.repo.list(featured_only=featured_only, active_only=active_only)

    def get_by_id(self, package_id: str) -> Package:
        pkg = self.repo.get_by_id(package_id)
        if not pkg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pacote não encontrado."
            )
        return pkg

    def create(self, package_in: PackageCreate) -> Package:
        existing = self.repo.get_by_id(package_in.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pacote com este ID já existe."
            )

        pkg = Package(**package_in.model_dump())
        return self.repo.create(pkg)

    def delete(self, package_id: str) -> None:
        pkg = self.get_by_id(package_id)
        self.repo.delete(pkg)

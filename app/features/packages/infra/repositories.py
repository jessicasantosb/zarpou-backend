from typing import List, Optional
from sqlalchemy.orm import Session
from app.features.packages.infra.models import Package


class PackageRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, featured_only: bool = False, active_only: bool = True) -> List[Package]:
        query = self.db.query(Package)
        if active_only:
            query = query.filter(Package.is_active == True)
        if featured_only:
            query = query.filter(Package.featured == True)
        return query.all()

    def get_by_id(self, package_id: str) -> Optional[Package]:
        return self.db.query(Package).filter(Package.id == package_id).first()

    def create(self, pkg: Package) -> Package:
        self.db.add(pkg)
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def delete(self, pkg: Package) -> None:
        self.db.delete(pkg)
        self.db.commit()

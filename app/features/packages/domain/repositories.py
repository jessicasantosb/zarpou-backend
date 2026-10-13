from typing import List, Optional, Protocol
from app.features.packages.domain.entities import PackageEntity


class IPackageRepository(Protocol):
    def list(self, featured_only: bool = False, active_only: bool = True) -> List[PackageEntity]:
        ...

    def get_by_id(self, package_id: str) -> Optional[PackageEntity]:
        ...

    def save(self, package: PackageEntity) -> PackageEntity:
        ...

    def delete(self, package_id: str) -> bool:
        ...

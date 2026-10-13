from typing import Optional, Protocol
from app.features.agency.domain.entities import AgencySettingEntity, HeroConfigEntity


class AgencyRepository(Protocol):
    def get_settings(self) -> Optional[AgencySettingEntity]:
        ...

    def get_hero(self) -> Optional[HeroConfigEntity]:
        ...

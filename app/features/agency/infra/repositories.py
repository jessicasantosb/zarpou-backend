from typing import Optional
from sqlalchemy.orm import Session
from app.features.agency.infra.models import AgencySetting, HeroConfig


class SqlAlchemyAgencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_settings(self) -> AgencySetting:
        setting = self.db.query(AgencySetting).filter(AgencySetting.id == "default").first()
        if not setting:
            setting = AgencySetting(id="default")
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        return setting

    def get_or_create_hero(self) -> HeroConfig:
        hero = self.db.query(HeroConfig).filter(HeroConfig.id == "default").first()
        if not hero:
            hero = HeroConfig(id="default")
            self.db.add(hero)
            self.db.commit()
            self.db.refresh(hero)
        return hero

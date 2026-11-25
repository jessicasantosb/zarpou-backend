import unicodedata

from sqlalchemy import Column, ForeignKey, Index, Integer, String

from app.core.database import Base


def search_key(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


class LocationCountry(Base):
    __tablename__ = "location_countries"

    code = Column(String(2), primary_key=True)
    name = Column(String(200), nullable=False)


class LocationState(Base):
    __tablename__ = "location_states"

    code = Column(String(32), primary_key=True)
    country_code = Column(String(2), ForeignKey("location_countries.code"), nullable=False, index=True)
    name = Column(String(200), nullable=False)


class LocationCity(Base):
    __tablename__ = "location_cities"
    __table_args__ = (
        Index("ix_location_city_country_name", "country_code", "search_name", "id"),
        Index("ix_location_city_state_name", "state_code", "search_name", "id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=False)
    country_code = Column(String(2), ForeignKey("location_countries.code"), nullable=False)
    state_code = Column(String(32), ForeignKey("location_states.code"), nullable=True)
    name = Column(String(200), nullable=False)
    search_name = Column(String(255), nullable=False)

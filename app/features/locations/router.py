from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.locations.models import LocationCity, LocationCountry, LocationState, search_key

router = APIRouter()
CountryCode = Annotated[str, Path(pattern=r"^[A-Za-z]{2}$")]


class CountryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class StateResponse(CountryResponse):
    country_code: str


class CityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_code: str
    state_code: str | None


@router.get("/countries", response_model=list[CountryResponse])
def list_countries(db: Session = Depends(get_db)):
    return db.scalars(select(LocationCountry).order_by(LocationCountry.name, LocationCountry.code)).all()


def require_country(country_code: str, db: Session) -> str:
    code = country_code.upper()
    if db.get(LocationCountry, code) is None:
        raise HTTPException(status_code=404, detail="País não encontrado.")
    return code


@router.get("/countries/{country_code}/states", response_model=list[StateResponse])
def list_states(country_code: CountryCode, db: Session = Depends(get_db)):
    code = require_country(country_code, db)
    statement = (
        select(LocationState)
        .where(LocationState.country_code == code)
        .order_by(LocationState.name, LocationState.code)
    )
    return db.scalars(statement).all()


@router.get("/countries/{country_code}/cities", response_model=list[CityResponse])
def list_cities(
    country_code: CountryCode,
    state_code: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    db: Session = Depends(get_db),
):
    code = require_country(country_code, db)
    statement = select(LocationCity).where(LocationCity.country_code == code)
    if state_code is not None:
        state = db.get(LocationState, state_code.strip().upper())
        if state is None or state.country_code != code:
            raise HTTPException(status_code=404, detail="Estado ou região não encontrado para este país.")
        statement = statement.where(LocationCity.state_code == state.code)
    prefix = search_key(q or "")
    if prefix:
        statement = statement.where(LocationCity.search_name.startswith(prefix, autoescape=True))
    statement = statement.order_by(LocationCity.search_name, LocationCity.id).offset(offset).limit(limit)
    return db.scalars(statement).all()

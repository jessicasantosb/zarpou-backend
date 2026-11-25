from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.features.locations.models import LocationCity, LocationCountry, LocationState
from app.main import app
from scripts import import_locations

CATALOG = "/api/v1/locations/countries"


@pytest.fixture
def catalog_client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'locations.db').as_posix()}")
    for table in (LocationCountry, LocationState, LocationCity):
        table.__table__.create(engine)

    def catalog_db():
        with Session(engine) as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, catalog_db)
    monkeypatch.setattr(import_locations, "engine", engine)
    monkeypatch.setattr(import_locations, "prepare_database_schema", lambda: None)
    yield TestClient(app)
    engine.dispose()


def city_row(city_id, name, country, state=""):
    row = [str(city_id), name] + [""] * 9
    row[8] = country
    row[10] = state
    return "\t".join(row)


@pytest.fixture
def catalog_source(tmp_path):
    (tmp_path / "countryInfo.txt").write_text(
        "# countryInfo\nBR\tBRA\t076\tBR\tBrazil\nSG\tSGP\t702\tSN\tSingapore\nUS\tUSA\t840\tUS\tUnited States\n",
        encoding="utf-8",
    )
    (tmp_path / "admin1CodesASCII.txt").write_text("BR.SP\tSão Paulo\nUS.CA\tCalifornia\n", encoding="utf-8")
    with ZipFile(tmp_path / "cities500.zip", "w") as archive:
        archive.writestr("cities500.txt", "\n".join([
            city_row(1, "São Paulo", "BR", "SP"),
            city_row(2, "São Carlos", "BR", "SP"),
            city_row(3, "Singapore", "SG"),
        ]))
    return tmp_path


def test_locations_routes_are_available_without_authentication(catalog_client):
    response = catalog_client.get(CATALOG)
    assert response.status_code == 200
    assert response.json() == []


def test_import_and_list_locations(catalog_client, catalog_source):
    assert import_locations.import_catalog(catalog_source) == (3, 2, 3)
    assert import_locations.import_catalog(catalog_source) == (3, 2, 3)
    assert [item["code"] for item in catalog_client.get(CATALOG).json()] == ["BR", "SG", "US"]
    assert catalog_client.get(f"{CATALOG}/br/states").json() == [
        {"code": "BR.SP", "name": "São Paulo", "country_code": "BR"},
    ]

    cities = f"{CATALOG}/BR/cities"
    query = {"state_code": "br.sp", "q": "SAO", "limit": 1}
    assert [item["name"] for item in catalog_client.get(cities, params=query).json()] == ["São Carlos"]
    query["offset"] = 1
    assert [item["name"] for item in catalog_client.get(cities, params=query).json()] == ["São Paulo"]
    assert catalog_client.get(cities, params={"q": "%"}).json() == []
    assert catalog_client.get(cities, params={"state_code": "US.CA"}).status_code == 404
    assert catalog_client.get(cities, params={"limit": 101}).status_code == 422
    assert catalog_client.get(f"{CATALOG}/ZZ/states").status_code == 404
    assert catalog_client.get(f"{CATALOG}/SG/states").json() == []
    assert catalog_client.get(f"{CATALOG}/SG/cities").json() == [
        {"id": 3, "name": "Singapore", "country_code": "SG", "state_code": None},
    ]


def test_failed_import_preserves_catalog(catalog_client, catalog_source):
    import_locations.import_catalog(catalog_source)
    with ZipFile(catalog_source / "cities500.zip", "w") as archive:
        archive.writestr("cities500.txt", "")

    with pytest.raises(ValueError, match="precisa conter cidades"):
        import_locations.import_catalog(catalog_source)

    assert len(catalog_client.get(f"{CATALOG}/BR/cities").json()) == 2

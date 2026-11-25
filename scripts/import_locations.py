"""Replace the reference catalog with the GeoNames country, ADM1 and cities500 exports."""

import argparse
from io import TextIOWrapper
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import httpx
from sqlalchemy import delete, insert, text

from app.core.database import engine
from app.features.locations.models import LocationCity, LocationCountry, LocationState, search_key
from app.main import prepare_database_schema

SOURCE_URL = "https://download.geonames.org/export/dump"
SOURCE_FILES = ("countryInfo.txt", "admin1CodesASCII.txt", "cities500.zip")
BATCH_SIZE = 1000


def tsv_rows(lines):
    for line in lines:
        if line.strip() and not line.startswith("#"):
            yield line.rstrip("\r\n").split("\t")


def download_files(destination: Path) -> None:
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for name in SOURCE_FILES:
            with client.stream("GET", f"{SOURCE_URL}/{name}") as response:
                response.raise_for_status()
                with (destination / name).open("wb") as output:
                    for chunk in response.iter_bytes():
                        output.write(chunk)


def import_catalog(source: Path) -> tuple[int, int, int]:
    with (source / "countryInfo.txt").open(encoding="utf-8-sig") as stream:
        countries = {row[0]: {"code": row[0], "name": row[4]} for row in tsv_rows(stream)}

    states = {}
    with (source / "admin1CodesASCII.txt").open(encoding="utf-8-sig") as stream:
        for row in tsv_rows(stream):
            code, name = row[0].upper(), row[1]
            country, _, _ = code.partition(".")
            if country in countries:
                states[code] = {"code": code, "country_code": country, "name": name}

    if not countries or not states:
        raise ValueError("Os arquivos de países e estados do GeoNames precisam conter dados.")

    prepare_database_schema()
    city_count = 0
    with ZipFile(source / "cities500.zip") as archive:
        with archive.open("cities500.txt") as raw, TextIOWrapper(raw, encoding="utf-8-sig") as stream:
            with engine.begin() as conn:
                if conn.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(715608235)"))
                conn.execute(delete(LocationCity))
                conn.execute(delete(LocationState))
                conn.execute(delete(LocationCountry))
                conn.execute(insert(LocationCountry), list(countries.values()))
                conn.execute(insert(LocationState), list(states.values()))

                batch = []
                for row in tsv_rows(stream):
                    country = row[8]
                    if country not in countries:
                        continue
                    state = f"{country}.{row[10]}".upper()
                    batch.append({
                        "id": int(row[0]),
                        "name": row[1],
                        "search_name": search_key(row[1]),
                        "country_code": country,
                        "state_code": state if state in states else None,
                    })
                    city_count += 1
                    if len(batch) == BATCH_SIZE:
                        conn.execute(insert(LocationCity), batch)
                        batch.clear()
                if not city_count:
                    raise ValueError("O arquivo de cidades do GeoNames precisa conter cidades dos países importados.")
                if batch:
                    conn.execute(insert(LocationCity), batch)

    return len(countries), len(states), city_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Diretório com os três arquivos originais do GeoNames.")
    args = parser.parse_args()

    if args.source_dir is not None:
        counts = import_catalog(args.source_dir)
    else:
        with TemporaryDirectory(prefix="fly-promo-geonames-") as directory:
            source = Path(directory)
            download_files(source)
            counts = import_catalog(source)

    countries, states, cities = counts
    print(f"GeoNames importado: {countries} países, {states} estados ou regiões e {cities} cidades.")


if __name__ == "__main__":
    main()

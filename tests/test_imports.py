"""
Testes da importação em massa de catálogo (CSV/Excel + fila Celery).

Cobertura dos critérios de aceite:
- Upload aceito e job disparado para processamento em background (sem 504).
- Validação/higienização: campos obrigatórios, tipos inválidos, código
  duplicado dentro da planilha e colunas obrigatórias ausentes.
- Upsert por código: linha existente é atualizada, inexistente é criada.
- Relatório de carga: sucesso/falha por linha com o motivo.
- Permissão herdada da tela admin de destino.
"""
import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.features.destinations.infra.models import Destination
from app.features.flights.infra.models import Flight
from app.features.hotels.infra.models import Hotel
from app.features.imports.app.services import recover_stale_jobs
from app.features.imports.infra.models import ImportJob
from app.features.promotions.infra.models import Promotion
from app.main import app

client = TestClient(app)

IMPORTS_URL = "/api/v1/imports"


@pytest.fixture(autouse=True)
def process_imports_synchronously(monkeypatch):
    """Substitui o enqueue Celery pelo processamento síncrono (sem Redis nos testes)."""
    from app.features.imports.app import services

    def _sync(job_id: str):
        services.process_import_job(job_id)

    monkeypatch.setattr(services, "dispatch_import_job", _sync)


def _admin_headers():
    db = SessionLocal()
    try:
        from app.models.user import User

        admin = db.query(User).filter(User.email == "admin@zarpou.com.br").first()
        assert admin is not None
        return {"Authorization": f"Bearer {create_access_token(subject=admin.id, role=admin.role)}"}
    finally:
        db.close()


def _csv(headers, rows) -> bytes:
    lines = [";".join(headers)]
    for row in rows:
        lines.append(";".join(row))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _upload(resource, content, filename="import.csv", headers=None):
    return client.post(
        f"{IMPORTS_URL}/{resource}",
        files={"file": (filename, content, "text/csv")},
        data={"mode": "upsert"},
        headers=headers or _admin_headers(),
    )


def _unique(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _fetch_job(job_id):
    res = client.get(f"{IMPORTS_URL}/jobs/{job_id}", headers=_admin_headers())
    assert res.status_code == 200
    return res.json()


# ---------------------------------------------------------------------------
# Fluxo feliz + relatório de carga
# ---------------------------------------------------------------------------

def test_import_hotels_happy_path_completes_with_report():
    id_a, id_b = _unique("hotel-a"), _unique("hotel-b")
    content = _csv(
        ["id", "name", "city", "image_url", "base_price_per_night", "stars", "amenities", "featured"],
        [
            [id_a, "Hotel Teste Import", "Recife", "https://img/x.jpg", "450.50", "4", "Piscina|Wi-Fi", "sim"],
            [id_b, "Hotel Dois Import", "Natal", "https://img/y.jpg", "700,00", "5", "", "nao"],
        ],
    )
    res = _upload("hotels", content)
    assert res.status_code == 202, res.text
    job = _fetch_job(res.json()["job"]["id"])

    assert job["status"] == "completed"
    assert job["total_rows"] == 2
    assert job["success_count"] == 2
    assert job["error_count"] == 0
    assert job["report"]["errors"] == []
    assert job["processed_rows"] == 2

    db = SessionLocal()
    try:
        hotel = db.query(Hotel).filter(Hotel.id == id_a).first()
        assert hotel is not None
        assert hotel.name == "Hotel Teste Import"
        assert float(hotel.base_price_per_night) == 450.50
        assert hotel.amenities == ["Piscina", "Wi-Fi"]
        assert hotel.featured is True
    finally:
        db.close()


def test_import_reports_row_errors_with_line_numbers_and_reasons():
    ok_id = _unique("hotel-ok")
    dup_id = _unique("hotel-dup")
    content = _csv(
        ["id", "name", "city", "image_url", "base_price_per_night", "stars"],
        [
            [ok_id, "Hotel OK", "Curitiba", "https://img/ok.jpg", "300", "4"],
            [dup_id, "Sem Cidade", "  ", "https://img/s.jpg", "300", "4"],       # linha 3: city vazio
            [_unique("hotel-x"), "Nota Ruim", "Belem", "https://img/x.jpg", "abc", "4"],  # linha 4: número inválido
            [ok_id, "Duplicado", "Belem", "https://img/d.jpg", "300", "4"],      # linha 5: id repetido
        ],
    )
    res = _upload("hotels", content)
    assert res.status_code == 202
    job = _fetch_job(res.json()["job"]["id"])

    assert job["status"] == "completed"
    assert job["success_count"] == 1
    assert job["error_count"] == 3

    by_row = {error["row"]: error for error in job["report"]["errors"]}
    assert set(by_row) == {3, 4, 5}
    assert "city" in by_row[3]["error"] and "obrigatório" in by_row[3]["error"]
    assert "base_price_per_night" in by_row[4]["error"]
    assert "duplicado" in by_row[5]["error"] and "linha 2" in by_row[5]["error"]
    assert by_row[5]["code"] == ok_id


# ---------------------------------------------------------------------------
# Upsert por código
# ---------------------------------------------------------------------------

def test_import_upsert_updates_existing_hotel():
    hotel_id = _unique("hotel-upd")
    db = SessionLocal()
    try:
        db.add(Hotel(id=hotel_id, name="Nome Antigo", city="Salvador",
                     image_url="https://img/old.jpg", base_price_per_night=999))
        db.commit()
    finally:
        db.close()

    content = _csv(
        ["id", "name", "base_price_per_night"],
        [[hotel_id, "Nome Atualizado", "550.00"]],
    )
    res = _upload("hotels", content)
    job = _fetch_job(res.json()["job"]["id"])
    assert job["status"] == "completed"
    assert job["success_count"] == 1

    db = SessionLocal()
    try:
        hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
        assert hotel.name == "Nome Atualizado"          # atualizado
        assert float(hotel.base_price_per_night) == 550  # preço atualizado
        assert hotel.city == "Salvador"                 # coluna fora do arquivo preservada
    finally:
        db.close()


def test_import_coupons_upsert_by_code_normalizes_and_updates():
    code = f"IMP{uuid.uuid4().hex[:6].upper()}"
    content = _csv(
        ["code", "discount_type", "discount_value"],
        [[code.lower(), "percent", "10"]],  # minúsculas devem ser normalizadas
    )
    res = _upload("coupons", content)
    job = _fetch_job(res.json()["job"]["id"])
    assert job["success_count"] == 1

    from app.features.coupons.infra.models import Coupon
    db = SessionLocal()
    try:
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        assert coupon is not None
        assert float(coupon.discount_value) == 10
        first_id = coupon.id
    finally:
        db.close()

    # segunda importação com o mesmo código atualiza (não duplica)
    res = _upload("coupons", _csv(["code", "discount_value"], [[code, "25"]]))
    job = _fetch_job(res.json()["job"]["id"])
    assert job["success_count"] == 1

    db = SessionLocal()
    try:
        assert db.query(Coupon).filter(Coupon.code == code).count() == 1
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        assert float(coupon.discount_value) == 25
        assert coupon.id == first_id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Estrutura do arquivo (falha de job, não de linha)
# ---------------------------------------------------------------------------

def test_missing_key_column_fails_the_job():
    """Sem a coluna-chave (id) não há como fazer upsert — falha estrutural do job."""
    content = _csv(["name", "city", "image_url", "base_price_per_night"],
                   [["Teste", "Recife", "https://img", "100"]])
    res = _upload("hotels", content)
    job = _fetch_job(res.json()["job"]["id"])
    assert job["status"] == "failed"
    assert "id" in job["message"]


def test_partial_update_without_required_columns_fails_only_on_creation():
    """Colunas obrigatórias não estão no cabeçalho: linhas que criam registros falham por linha."""
    content = _csv(
        ["id", "name"],
        [[_unique("hotel-novo"), "Só o Nome"]],
    )
    res = _upload("hotels", content)
    job = _fetch_job(res.json()["job"]["id"])
    assert job["status"] == "completed"
    assert job["success_count"] == 0
    assert job["error_count"] == 1
    assert "obrigat" in job["report"]["errors"][0]["error"]


def test_unsupported_extension_rejected():
    res = _upload("hotels", b"qualquer", filename="planilha.txt")
    assert res.status_code == 400
    assert "csv" in res.json()["detail"].lower()


def test_unknown_resource_returns_404():
    res = _upload("naoexiste", b"id\nx\n")
    assert res.status_code == 404


def test_import_requires_admin_authentication():
    res = client.post(
        f"{IMPORTS_URL}/hotels",
        files={"file": ("import.csv", b"id\nx\n", "text/csv")},
    )
    assert res.status_code == 401


def test_import_permission_follows_target_screen():
    """Usuário com apenas a tela 'destinos' importa destinos, mas não hotéis."""
    db = SessionLocal()
    try:
        from app.models.user import User

        user = User(
            id=f"imp-user-{uuid.uuid4().hex[:8]}",
            name="Editor Destinos",
            email=f"import.destinos.{uuid.uuid4().hex[:8]}@exemplo.com",
            password_hash="x",  # nunca será usado (o token é assinado direto no teste)
            role="personalizado",
        )
        user.allowed_screens = ["destinos"]
        db.add(user)
        db.commit()
        user_id = user.id
        headers = {"Authorization": f"Bearer {create_access_token(subject=user.id, role=user.role)}"}
    finally:
        db.close()

    try:
        res = _upload("hotels", _csv(["id"], [["x"]]), headers=headers)
        assert res.status_code == 403

        content = _csv(
            ["id", "title", "country", "image_url"],
            [[_unique("dest-imp"), "Teste Noruega", "Noruega", "https://img/n.jpg"]],
        )
        res = _upload("destinations", content, headers=headers)
        assert res.status_code == 202
        job = _fetch_job(res.json()["job"]["id"])
        assert job["status"] == "completed"
        assert job["success_count"] == 1
    finally:
        # limpa o usuário de teste (o banco de dev é compartilhado e persistente)
        db = SessionLocal()
        try:
            from app.models.user import User as UserModel

            db.query(UserModel).filter(UserModel.id == user_id).delete()
            db.commit()
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Demais recursos do 1º lote (smoke) + XLSX
# ---------------------------------------------------------------------------

def test_import_destinations_flights_promotions_smoke():
    dest_id, flight_id, promo_id = _unique("dest"), _unique("flight"), _unique("promo")

    res = _upload("destinations", _csv(
        ["id", "title", "country", "image_url", "category", "starting_price"],
        [[dest_id, "Lofoten", "Noruega", "https://img/l.jpg", "Nacional", "8900,00"]],
    ))
    assert _fetch_job(res.json()["job"]["id"])["success_count"] == 1

    res = _upload("flights", _csv(
        ["id", "price", "region", "is_round_trip"],
        [[flight_id, "3200.90", "europe", "sim"]],
    ))
    assert _fetch_job(res.json()["job"]["id"])["success_count"] == 1

    res = _upload("promotions", _csv(
        ["id", "title", "image_url", "link", "start_date"],
        [[promo_id, "Promo Import", "https://img/p.jpg", "/promocoes/x", "20/12/2026"]],
    ))
    assert _fetch_job(res.json()["job"]["id"])["success_count"] == 1

    db = SessionLocal()
    try:
        assert db.query(Destination).filter(Destination.id == dest_id).first().category == "national"
        assert db.query(Flight).filter(Flight.id == flight_id).first().region == "europe"
        assert db.query(Promotion).filter(Promotion.id == promo_id).first().start_date.day == 20
    finally:
        db.close()


def test_import_xlsx_file():
    import openpyxl

    hotel_id = _unique("hotel-xlsx")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["id", "name", "city", "image_url", "base_price_per_night"])
    sheet.append([hotel_id, "Hotel via Excel", "Manaus", "https://img/m.jpg", "399.90"])
    buffer = io.BytesIO()
    workbook.save(buffer)

    res = _upload("hotels", buffer.getvalue(), filename="catalogo.xlsx")
    assert res.status_code == 202
    job = _fetch_job(res.json()["job"]["id"])
    assert job["status"] == "completed"
    assert job["success_count"] == 1

    db = SessionLocal()
    try:
        assert db.query(Hotel).filter(Hotel.id == hotel_id).first().name == "Hotel via Excel"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Templates + histórico + recuperação de jobs órfãos
# ---------------------------------------------------------------------------

def test_template_download_csv_and_xlsx():
    res = client.get(f"{IMPORTS_URL}/hotels/template", headers=_admin_headers())
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "template-hotels.csv" in res.headers["content-disposition"]
    body = res.content.decode("utf-8-sig")
    assert body.splitlines()[0].startswith("id;name;city")

    res = client.get(f"{IMPORTS_URL}/hotels/template?format=xlsx", headers=_admin_headers())
    assert res.status_code == 200
    import openpyxl

    workbook = openpyxl.load_workbook(io.BytesIO(res.content))
    headers = [cell.value for cell in workbook.active[1]]
    assert "base_price_per_night" in headers


def test_jobs_history_lists_recent_imports():
    res = _upload("promotions", _csv(
        ["id", "title", "image_url", "link"],
        [[_unique("promo-hist"), "Histórico", "https://img/h.jpg", "/x"]],
    ))
    job_id = res.json()["job"]["id"]
    res = client.get(f"{IMPORTS_URL}/promotions/jobs", headers=_admin_headers())
    assert res.status_code == 200
    assert any(job["id"] == job_id for job in res.json())


def test_stale_pending_jobs_are_marked_failed_on_startup_sweep():
    from datetime import datetime, timedelta, timezone

    job = ImportJob(
        id=str(uuid.uuid4()),
        resource="hotels",
        status="processing",
        original_filename="antigo.csv",
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    db = SessionLocal()
    try:
        db.add(job)
        db.commit()
        assert recover_stale_jobs(db) >= 1
        db.refresh(job)
        assert job.status == "failed"
        assert "reiniciado" in job.message
    finally:
        db.close()

import re
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.features.coupons.infra.models import Coupon

client = TestClient(app)


def _admin_headers() -> dict:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@zarpou.com.br", "password": "admin123"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _operator_without_coupons_headers() -> dict:
    # Juliana (conftest) é 'personalizado' e não possui a tela 'cupons' em allowed_screens
    token = create_access_token(subject="adm-2", role="personalizado")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def _cleanup_coupons():
    yield
    db = SessionLocal()
    try:
        db.query(Coupon).filter(Coupon.code.like("TESTE%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_coupons_list_requires_auth():
    res = client.get("/api/v1/coupons")
    assert res.status_code == 401


def test_coupons_blocked_for_operator_without_screen():
    res = client.get("/api/v1/coupons", headers=_operator_without_coupons_headers())
    assert res.status_code == 403
    assert "cupons" in res.json()["detail"].lower()


def test_coupon_full_crud_flow(_cleanup_coupons):
    headers = _admin_headers()
    code = f"TESTE{int(time.time())}"

    # CREATE
    create_res = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={
            "code": code.lower(),  # deve ser normalizado para maiúsculas
            "description": "Cupom de teste da suíte",
            "discount_type": "percent",
            "discount_value": 10,
            "max_uses": 100,
            "valid_from": "2026-10-17",
            "valid_to": "2026-12-31",
        },
    )
    assert create_res.status_code == 201, create_res.text
    coupon = create_res.json()
    assert coupon["code"] == code
    assert coupon["used_count"] == 0
    coupon_id = coupon["id"]

    # DUPLICATE CODE -> 409
    dup_res = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={"code": code, "discount_type": "fixed", "discount_value": 25},
    )
    assert dup_res.status_code == 409

    # LIST
    list_res = client.get("/api/v1/coupons", headers=headers, params={"search": code})
    assert list_res.status_code == 200
    assert any(c["id"] == coupon_id for c in list_res.json())

    # GET BY ID
    get_res = client.get(f"/api/v1/coupons/{coupon_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["discount_value"] == 10

    # UPDATE
    update_res = client.put(
        f"/api/v1/coupons/{coupon_id}",
        headers=headers,
        json={"discount_value": 15, "description": "Cupom atualizado"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["discount_value"] == 15
    assert update_res.json()["description"] == "Cupom atualizado"

    # TOGGLE
    toggle_res = client.patch(f"/api/v1/coupons/{coupon_id}/toggle", headers=headers)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["active"] is False

    # VALIDAÇÕES DE NEGÓCIO
    invalid_percent = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={"code": f"TESTEINV{int(time.time())}", "discount_type": "percent", "discount_value": 150},
    )
    assert invalid_percent.status_code == 400

    invalid_dates = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={
            "code": f"TESTEDAT{int(time.time())}",
            "discount_type": "fixed",
            "discount_value": 10,
            "valid_from": "2026-12-31",
            "valid_to": "2026-10-17",
        },
    )
    assert invalid_dates.status_code == 400

    # DELETE
    del_res = client.delete(f"/api/v1/coupons/{coupon_id}", headers=headers)
    assert del_res.status_code == 204

    gone_res = client.get(f"/api/v1/coupons/{coupon_id}", headers=headers)
    assert gone_res.status_code == 404


def test_generate_random_code():
    headers = _admin_headers()

    # Requer admin
    assert client.post("/api/v1/coupons/generate-code", json={}).status_code == 401

    # Com prefixo (normalizado para maiúsculas) e tamanho definido
    res1 = client.post(
        "/api/v1/coupons/generate-code",
        headers=headers,
        json={"prefix": "black", "length": 8},
    )
    assert res1.status_code == 200
    code1 = res1.json()["code"]
    assert re.fullmatch(r"BLACK[A-Z2-9]{8}", code1)

    # Sem prefixo: só maiúsculas e dígitos, sem caracteres ambíguos (0, O, 1, I, L)
    res2 = client.post("/api/v1/coupons/generate-code", headers=headers, json={})
    assert res2.status_code == 200
    code2 = res2.json()["code"]
    assert re.fullmatch(r"[A-Z2-9]{10}", code2)
    assert code1 != code2


def test_validate_coupon_public_endpoint(_cleanup_coupons):
    headers = _admin_headers()
    code = f"TESTEVAL{int(time.time())}"

    create_res = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={
            "code": code,
            "discount_type": "percent",
            "discount_value": 10,
            "min_order_amount": 100,
            "valid_from": "2026-01-01",
            "valid_to": "2099-12-31",
        },
    )
    assert create_res.status_code == 201, create_res.text

    # Endpoint é público (sem Authorization) e normaliza o código para maiúsculas
    ok = client.post("/api/v1/coupons/validate", json={"code": code.lower(), "order_amount": 200})
    assert ok.status_code == 200
    body = ok.json()
    assert body["valid"] is True
    assert body["code"] == code
    assert body["discount_type"] == "percent"
    assert body["discount_amount"] == 20.0

    # Código inexistente
    missing = client.post("/api/v1/coupons/validate", json={"code": "NAOEXISTE99", "order_amount": 200})
    assert missing.status_code == 400
    assert "não encontrado" in missing.json()["detail"]

    # Abaixo do pedido mínimo
    below = client.post("/api/v1/coupons/validate", json={"code": code, "order_amount": 50})
    assert below.status_code == 400
    assert "mínimo" in below.json()["detail"].lower()

    # Desativado → não pode ser usado
    coupon_id = create_res.json()["id"]
    client.patch(f"/api/v1/coupons/{coupon_id}/toggle", headers=headers)
    inactive = client.post("/api/v1/coupons/validate", json={"code": code, "order_amount": 200})
    assert inactive.status_code == 400
    assert "desativado" in inactive.json()["detail"]


def test_checkout_with_coupon_discount(_cleanup_coupons):
    headers = _admin_headers()
    code = f"TESTECK{int(time.time())}"

    create_res = client.post(
        "/api/v1/coupons",
        headers=headers,
        json={"code": code, "discount_type": "fixed", "discount_value": 100, "per_customer_limit": 5},
    )
    assert create_res.status_code == 201, create_res.text
    coupon_id = create_res.json()["id"]

    hotels = client.get("/api/v1/hotels").json()
    assert hotels, "Seed de hotéis é necessário para o teste de checkout com cupom"
    hotel = hotels[0]
    room = hotel["rooms"][0]

    booking_payload = {
        "productType": "hotel",
        "hotelId": hotel["id"],
        "selectedRoomId": room["id"],
        "checkInDate": "2026-11-20",
        "checkOutDate": "2026-11-25",
        "nights": 5,
        "adults": 2,
        "children": 0,
        "travelers": [
            {
                "fullName": "Cliente Teste Cupom",
                "email": "cliente.cupom@exemplo.com",
                "documentType": "CPF",
                "documentNumber": "123.456.789-00",
                "phone": "(11) 99887-6655",
                "birthDate": "1992-05-15",
                "gender": "F",
                "isPrimary": True,
            }
        ],
        "addons": [],
        "paymentMethod": "credit_card",
        "installments": 1,
        "couponCode": code.lower(),  # deve ser normalizado para maiúsculas
    }
    res = client.post("/api/v1/bookings/checkout", json=booking_payload)
    assert res.status_code == 201, res.text
    data = res.json()

    base = round(float(room["price_per_night"]) * 5, 2)
    taxes = round(base * 0.05, 2)
    expected_discount = round(min(100.0, base + taxes), 2)
    pricing = data["pricing"]
    assert data["couponCode"] == code
    assert pricing["discountAmount"] == pytest.approx(expected_discount, abs=0.01)
    assert pricing["finalAmount"] == pytest.approx(base + taxes - expected_discount, abs=0.01)

    # Uso registrado no cupom
    check = client.get(f"/api/v1/coupons/{coupon_id}", headers=headers)
    assert check.json()["used_count"] == 1

    # Checkout com cupom inválido falha a reserva inteira
    bad_payload = dict(booking_payload)
    bad_payload["couponCode"] = "CUPOMQUENAOEXISTE"
    bad_res = client.post("/api/v1/bookings/checkout", json=bad_payload)
    assert bad_res.status_code == 400

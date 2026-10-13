import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.user import User
from app.models.customer import Customer

client = TestClient(app)


def test_admin_cannot_deactivate_self():
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@zarpou.com.br").first()
    db.close()
    assert admin is not None

    token = create_access_token(subject=admin.id, role=admin.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Tentativa do admin desativar a própria conta deve retornar HTTP 400
    res = client.patch(f"/api/v1/users/{admin.id}/status", json={"is_active": False}, headers=headers)
    assert res.status_code == 400
    assert "próprio usuário" in res.json()["detail"].lower()


def test_admin_can_toggle_other_admin_status():
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@zarpou.com.br").first()
    other_admin = db.query(User).filter(User.email == "juliana.costa@zarpou.com.br").first()
    db.close()
    assert admin is not None
    assert other_admin is not None

    token = create_access_token(subject=admin.id, role=admin.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Desativa Juliana
    res = client.patch(f"/api/v1/users/{other_admin.id}/status", json={"is_active": False}, headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # Reativa Juliana
    res2 = client.patch(f"/api/v1/users/{other_admin.id}/status", json={"is_active": True}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["is_active"] is True


def test_list_customers_and_toggle_status():
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@zarpou.com.br").first()
    db.close()

    token = create_access_token(subject=admin.id, role=admin.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Listagem de clientes
    res = client.get("/api/v1/customers", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first_cust = data[0]
    cust_id = first_cust["id"]

    # Toggle status do cliente
    res_toggle = client.patch(f"/api/v1/customers/{cust_id}/status", json={"is_active": False}, headers=headers)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] is False

    # Reativa cliente
    res_toggle_back = client.patch(f"/api/v1/customers/{cust_id}/status", json={"is_active": True}, headers=headers)
    assert res_toggle_back.status_code == 200
    assert res_toggle_back.json()["is_active"] is True


def test_non_admin_cannot_access_users_endpoint():
    db = SessionLocal()
    gestor = db.query(User).filter(User.email == "juliana.costa@zarpou.com.br").first()
    db.close()
    assert gestor is not None

    token = create_access_token(subject=gestor.id, role=gestor.role)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/users", headers=headers)
    assert res.status_code == 403
    assert "administradores" in res.json()["detail"].lower()

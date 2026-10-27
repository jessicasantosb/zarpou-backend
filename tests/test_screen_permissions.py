import time
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.user import User

client = TestClient(app)


def test_superadmin_has_access_to_all_screens():
    # 1. Login com admin geral
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@zarpou.com.br", "password": "admin123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    user_info = login_res.json()["user"]
    assert "allowedScreens" in user_info
    assert len(user_info["allowedScreens"]) == 11
    assert "hospedagens" in user_info["allowedScreens"]
    assert "cupons" in user_info["allowedScreens"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Testa acesso ao dashboard
    metrics_res = client.get("/api/v1/agency/metrics", headers=headers)
    assert metrics_res.status_code == 200

    # 3. Testa acesso aos clientes
    cust_res = client.get("/api/v1/customers", headers=headers)
    assert cust_res.status_code == 200

    # 4. Testa acesso às reservas
    bookings_res = client.get("/api/v1/bookings", headers=headers)
    assert bookings_res.status_code == 200


def test_restricted_operator_is_blocked_on_unauthorized_screens():
    # 1. Cria operador pelo Superadmin com permissão APENAS para 'hospedagens'
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@zarpou.com.br", "password": "admin123"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    email_op = f"operador.hotel.{int(time.time())}@zarpou.com.br"
    create_res = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Operador Hotel",
            "email": email_op,
            "password": "SenhaOperador123!",
            "role": "gestor",
            "allowedScreens": ["hospedagens"],
        },
    )
    assert create_res.status_code == 201, create_res.text
    created_id = create_res.json()["id"]

    # 2. Login com o operador restrito
    op_login = client.post(
        "/api/v1/auth/login",
        json={"email": email_op, "password": "SenhaOperador123!"},
    )
    assert op_login.status_code == 200
    op_token = op_login.json()["access_token"]
    op_user = op_login.json()["user"]
    assert op_user["allowedScreens"] == ["hospedagens"]

    op_headers = {"Authorization": f"Bearer {op_token}"}

    # 3. Tenta acessar tela de Usuários/Clientes (tela 'usuarios') -> DEVE RETORNAR 403
    cust_res = client.get("/api/v1/customers", headers=op_headers)
    assert cust_res.status_code == 403
    assert "usuarios" in cust_res.json()["detail"].lower()

    # 4. Tenta acessar tela de Reservas (tela 'reservas') -> DEVE RETORNAR 403
    book_res = client.get("/api/v1/bookings", headers=op_headers)
    assert book_res.status_code == 403
    assert "reservas" in book_res.json()["detail"].lower()

    # 5. Tenta acessar Dashboard/Métricas (tela 'dashboard') -> DEVE RETORNAR 403
    metrics_res = client.get("/api/v1/agency/metrics", headers=op_headers)
    assert metrics_res.status_code == 403
    assert "dashboard" in metrics_res.json()["detail"].lower()

    # 6. Tenta cadastrar um Hotel (tela 'hospedagens' - PERMITIDA) -> DEVE TER SUCESSO (201)
    hotel_id = f"hotel-test-{int(time.time())}"
    hotel_res = client.post(
        "/api/v1/hotels",
        headers=op_headers,
        json={
            "id": hotel_id,
            "name": "Hotel Teste Permissão",
            "city": "Belo Horizonte",
            "state": "MG",
            "country": "Brasil",
            "stars": 4,
            "rating": 4.5,
            "review_count": 10,
            "description": "Hotel para teste de permissão",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945",
            "base_price_per_night": 350.0,
            "featured": False,
            "is_active": True,
            "rooms": [],
        },
    )
    assert hotel_res.status_code == 201, hotel_res.text

    # 7. Superadmin concede permissão de 'reservas' ao operador
    update_res = client.put(
        f"/api/v1/users/{created_id}",
        headers=admin_headers,
        json={"allowedScreens": ["hospedagens", "reservas"]},
    )
    assert update_res.status_code == 200

    # 8. Agora o operador tenta novamente acessar /bookings -> DEVE TER SUCESSO (200)
    book_res2 = client.get("/api/v1/bookings", headers=op_headers)
    assert book_res2.status_code == 200

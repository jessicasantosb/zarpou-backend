import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.two_factor import generate_totp_code

client = TestClient(app)


def test_security_headers_present():
    """Valida se os Security Headers HTTP defensivos (OWASP A05) estão sendo injetados."""
    res = client.get("/")
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in res.headers
    assert "Permissions-Policy" in res.headers


def test_idor_protection_on_bookings():
    """Valida que consultas por localizador/id sem autenticação nem email são bloqueadas (OWASP A01)."""
    # Consulta a um localizador inexistente ou sem email/permissão retorna 404
    res = client.get("/api/v1/bookings/locator/ZRP-999999")
    assert res.status_code == 404

    res2 = client.get("/api/v1/bookings/ZRP-999999")
    assert res2.status_code == 404


def test_token_revocation_and_logout():
    """Valida revogação imediata de token no logout (OWASP A07)."""
    # 1. Login admin
    login_res = client.post("/api/v1/auth/login", json={"email": "admin@zarpou.com.br", "password": "admin123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    refresh_token = login_res.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Testa endpoint protegido com token válido
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    # 3. Executa logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers, json={"refreshToken": refresh_token})
    assert logout_res.status_code == 200
    assert logout_res.json()["revokedTokens"] >= 1

    # 4. Testa novamente com o token revogado -> Deve ser 401
    me_after_logout = client.get("/api/v1/auth/me", headers=headers)
    assert me_after_logout.status_code == 401
    assert "Sessão encerrada" in me_after_logout.json()["detail"]

    # 5. Tenta renovar com refresh_token revogado -> Deve ser 401
    refresh_res = client.post("/api/v1/auth/refresh", json={"refreshToken": refresh_token})
    assert refresh_res.status_code == 401


def test_lgpd_consent_export_and_anonymization():
    """Valida fluxo de consentimento (Art. 8º), portabilidade (Art. 18 V) e anonimização (Art. 18 IV)."""
    unique_ts = int(time.time() * 1000)
    email = f"lgpd.test.{unique_ts}@example.com"
    pwd = "MinhaSenhaForte123!"

    # 1. Registro do cliente
    reg_res = client.post(
        "/api/v1/auth/customer/register",
        json={
            "name": "Maria LGPD Silva",
            "email": email,
            "password": pwd,
            "phone": "31988887777",
            "cpf": "12345678909",
        },
    )
    assert reg_res.status_code == 201

    # 2. Login
    login_res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    cust_headers = {"Authorization": f"Bearer {token}"}

    # 3. Registrar consentimento
    consent_res = client.post(
        "/api/v1/customers/me/consent",
        headers=cust_headers,
        json={
            "acceptedPrivacyPolicy": True,
            "acceptedTermsOfUse": True,
            "version": "2.0",
            "whatsappPromotions": True,
            "emailPromotions": False,
        },
    )
    assert consent_res.status_code == 200
    assert consent_res.json()["consent"]["acceptedPrivacyPolicy"] is True

    # 4. Consultar consentimento
    get_consent = client.get("/api/v1/customers/me/consent", headers=cust_headers)
    assert get_consent.status_code == 200
    assert get_consent.json()["consent"]["version"] == "2.0"

    # 5. Exportar dados pessoais (Portabilidade LGPD)
    export_res = client.get("/api/v1/customers/me/export-data", headers=cust_headers)
    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["profile"]["email"] == email
    assert export_data["controller"]["name"] == "Zarpou Viagens e Turismo Ltda"

    # 6. Anonimizar/Excluir conta (Direito ao Esquecimento)
    del_res = client.request(
        "DELETE",
        "/api/v1/customers/me",
        headers=cust_headers,
        json={"confirm": True, "password": pwd},
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # 7. Token deve ter sido revogado no delete
    after_del = client.get("/api/v1/customers/me/consent", headers=cust_headers)
    assert after_del.status_code == 401

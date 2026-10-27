"""
Testes anti-enumeração do fluxo de autenticação de clientes (2026-10-19):

As respostas de login/cadastro NÃO podem confirmar que um e-mail pertence a um
administrador da agência (nem revelar a rota do painel). O bloqueio de contas
admin na área de clientes permanece — muda apenas a mensagem, que passa a ser
genérica e idêntica aos demais casos de falha.

Regressão: antes desta correção, um atacante podia sondar
POST /auth/customer/login com qualquer e-mail e, pela mensagem específica
("Este e-mail pertence a um administrador... Painel Administrativo (/admin/login)"),
confirmar contas privilegiadas e mapear a rota do painel.
"""
import time

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

LOGIN_URL = "/api/v1/auth/customer/login"
REGISTER_URL = "/api/v1/auth/customer/register"
ADMIN_EMAIL = "admin@zarpou.com.br"


def _register_customer() -> str:
    email = f"enum.teste.{int(time.time() * 1000)}@exemplo.com"
    res = client.post(
        REGISTER_URL,
        json={"name": "Cliente Enum", "email": email, "password": "SenhaEnum123"},
    )
    assert res.status_code == 201, res.text
    return email


def test_admin_email_login_gives_generic_wrong_credentials_message():
    """Login com e-mail de admin responde igual a senha errada (sem oráculo)."""
    customer_email = _register_customer()

    res_admin = client.post(
        LOGIN_URL, json={"email": ADMIN_EMAIL, "password": "qualquer123"}
    )
    res_wrong_password = client.post(
        LOGIN_URL, json={"email": customer_email, "password": "senhaErrada999"}
    )

    assert res_admin.status_code == 400
    assert res_wrong_password.status_code == 400
    # mesma resposta — não dá para distinguir "é admin" de "senha errada"
    assert res_admin.json() == res_wrong_password.json()
    body_text = res_admin.text.lower()
    assert "administrador" not in body_text
    assert "/admin" not in body_text


def test_register_admin_email_matches_register_existing_account_message():
    """Cadastro com e-mail de admin responde igual a e-mail já cadastrado."""
    customer_email = _register_customer()

    res_admin = client.post(
        REGISTER_URL,
        json={"name": "Tentei Registrar", "email": ADMIN_EMAIL, "password": "Qualquer123"},
    )
    res_existing = client.post(
        REGISTER_URL,
        json={"name": "Tentei Registrar", "email": customer_email, "password": "Qualquer123"},
    )

    assert res_admin.status_code == res_existing.status_code == 400
    assert res_admin.json() == res_existing.json()
    body_text = res_admin.text.lower()
    assert "administrador" not in body_text
    assert "/admin" not in body_text


def test_unknown_email_login_equals_wrong_password_response():
    """Sem auto-criação no login: e-mail desconhecido responde igual a senha
    errada — o 400 deixa de ser um oráculo de "essa conta existe" (backlog #1)."""
    customer_email = _register_customer()

    res_unknown = client.post(
        LOGIN_URL, json={"email": "nunca.cadastrado.z@exemplo.com", "password": "Qualquer123"}
    )
    res_wrong_password = client.post(
        LOGIN_URL, json={"email": customer_email, "password": "senhaErrada999"}
    )

    assert res_unknown.status_code == res_wrong_password.status_code == 400
    assert res_unknown.json() == res_wrong_password.json()

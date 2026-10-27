"""
Testes do fluxo de recuperação de senha por e-mail (cliente B2C).

Cobertura de segurança:
- Resposta idêntica exista ou não a conta (anti enumeração de e-mails).
- Token aleatório de 32 bytes, guardado APENAS como hash SHA-256.
- Uso único, expiração de 30 minutos, novas solicitações invalidam links anteriores.
- Senha nova segue a mesma política do cadastro (mínimo 6 caracteres).
"""
import hashlib
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.customer import Customer, CustomerPasswordResetToken

client = TestClient(app)

REGISTER_URL = "/api/v1/auth/customer/register"
FORGOT_URL = "/api/v1/auth/customer/password/forgot"
RESET_URL = "/api/v1/auth/customer/password/reset"
LOGIN_URL = "/api/v1/auth/customer/login"


@pytest.fixture
def captured_reset_urls(monkeypatch):
    """Captura os links de redefinição que seriam enviados por e-mail."""
    urls = []

    def fake_send(name: str, email: str, reset_url: str) -> None:
        urls.append({"name": name, "email": email, "url": reset_url})

    monkeypatch.setattr(
        "app.features.auth.app.services.send_password_reset_email", fake_send
    )
    return urls


def _token_from_url(reset_url: str) -> str:
    return parse_qs(urlparse(reset_url).query)["token"][0]


def _register_customer(suffix: str, password: str = "SenhaOrigem123") -> dict:
    email = f"recupera.{suffix}.{int(time.time() * 1000)}@exemplo.com"
    res = client.post(
        REGISTER_URL,
        json={"name": "Cliente Recupera", "email": email, "password": password},
    )
    assert res.status_code == 201, res.text
    return {"email": email, "password": password}


def test_forgot_unknown_email_returns_generic_message_and_sends_no_email(
    captured_reset_urls,
):
    res = client.post(FORGOT_URL, json={"email": "naoexiste.zarpou@exemplo.com"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "cadastrado" in body["message"]
    assert captured_reset_urls == []  # nenhum e-mail disparado


def test_forgot_known_email_matches_unknown_email_response(captured_reset_urls):
    """A resposta para e-mail cadastrado é idêntica à de e-mail inexistente (anti enumeração)."""
    cust = _register_customer("anti.enum")

    res_known = client.post(FORGOT_URL, json={"email": cust["email"]})
    res_unknown = client.post(FORGOT_URL, json={"email": "outro.inexistente.z@exemplo.com"})

    assert res_known.status_code == res_unknown.status_code == 200
    assert res_known.json() == res_unknown.json()


def test_forgot_stores_only_sha256_hash_and_validates_link(captured_reset_urls):
    cust = _register_customer("hash")

    res = client.post(FORGOT_URL, json={"email": cust["email"]})
    assert res.status_code == 200
    assert len(captured_reset_urls) == 1

    sent = captured_reset_urls[0]
    assert sent["email"] == cust["email"]
    raw_token = _token_from_url(sent["url"])
    assert len(raw_token) >= 40  # token_urlsafe(32) → ~43 chars

    db = SessionLocal()
    try:
        row = (
            db.query(CustomerPasswordResetToken)
            .join(Customer, Customer.id == CustomerPasswordResetToken.customer_id)
            .filter(Customer.email == cust["email"])
            .first()
        )
        assert row is not None
        # no banco existe apenas o hash SHA-256, nunca o token em texto puro
        assert row.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert raw_token not in row.token_hash
        assert row.used_at is None
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        assert expires > datetime.now(timezone.utc)
    finally:
        db.close()


def test_reset_full_flow_changes_password_and_token_is_single_use(captured_reset_urls):
    cust = _register_customer("fluxo")

    client.post(FORGOT_URL, json={"email": cust["email"]})
    raw_token = _token_from_url(captured_reset_urls[0]["url"])

    new_password = "NovaSenhaForte123"
    res = client.post(RESET_URL, json={"token": raw_token, "password": new_password})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # senha antiga deixa de funcionar
    res = client.post(LOGIN_URL, json={"email": cust["email"], "password": cust["password"]})
    assert res.status_code == 400

    # nova senha funciona
    res = client.post(LOGIN_URL, json={"email": cust["email"], "password": new_password})
    assert res.status_code == 200
    assert res.json()["access_token"]

    # token é de uso único: segunda tentativa com o mesmo token falha
    res = client.post(RESET_URL, json={"token": raw_token, "password": "OutraSenha123"})
    assert res.status_code == 400


def test_reset_revokes_existing_access_and_refresh_tokens(captured_reset_urls):
    """Tokens emitidos antes do reset deixam de valer (SECURITY_BACKLOG #2)."""
    cust = _register_customer("revoga.sessao")

    login = client.post(LOGIN_URL, json=cust)
    assert login.status_code == 200
    old_access = login.json()["access_token"]
    old_refresh = login.json()["refresh_token"]

    # a sessão antiga funciona antes do reset
    me = client.get(
        "/api/v1/auth/customer/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert me.status_code == 200

    # garante fronteira de segundo entre emissão do token e marca de revogação
    # (o iat tem precisão de segundos; token do mesmo segundo é considerado novo)
    time.sleep(1.1)

    client.post(FORGOT_URL, json={"email": cust["email"]})
    raw_token = _token_from_url(captured_reset_urls[0]["url"])
    res = client.post(RESET_URL, json={"token": raw_token, "password": "NovaSenhaRevogada1"})
    assert res.status_code == 200

    # access token antigo → derrubado imediatamente
    me2 = client.get(
        "/api/v1/auth/customer/me", headers={"Authorization": f"Bearer {old_access}"}
    )
    assert me2.status_code == 401

    # refresh token antigo → também revogado (sessão comprometida não sobrevive)
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_res.status_code == 401

    # um novo login emite tokens válidos normalmente
    login2 = client.post(
        LOGIN_URL, json={"email": cust["email"], "password": "NovaSenhaRevogada1"}
    )
    assert login2.status_code == 200
    new_access = login2.json()["access_token"]
    me3 = client.get(
        "/api/v1/auth/customer/me", headers={"Authorization": f"Bearer {new_access}"}
    )
    assert me3.status_code == 200


def test_reset_with_garbage_token_rejected():
    res = client.post(
        RESET_URL,
        json={"token": "a" * 43, "password": "QualquerSenha123"},
    )
    assert res.status_code == 400


def test_reset_with_expired_token_rejected():
    # Token único por execução (o banco de testes é compartilhado e persistente)
    raw_token = f"token-expirado-{int(time.time() * 1000)}-" + "x" * 10
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    db = SessionLocal()
    try:
        cust = db.query(Customer).filter(Customer.email.like("recupera.%@exemplo.com")).first()
        assert cust is not None
        db.add(
            CustomerPasswordResetToken(
                customer_id=cust.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        db.commit()
    finally:
        db.close()

    try:
        res = client.post(RESET_URL, json={"token": raw_token, "password": "SenhaNova123"})
        assert res.status_code == 400
    finally:
        db = SessionLocal()
        try:
            db.query(CustomerPasswordResetToken).filter(
                CustomerPasswordResetToken.token_hash == token_hash
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_reset_with_weak_password_rejected_by_schema(captured_reset_urls):
    cust = _register_customer("fraca")
    client.post(FORGOT_URL, json={"email": cust["email"]})
    raw_token = _token_from_url(captured_reset_urls[0]["url"])

    res = client.post(RESET_URL, json={"token": raw_token, "password": "abc"})
    assert res.status_code == 422  # min_length=6 no schema


def test_new_forgot_invalidates_previous_links(captured_reset_urls):
    cust = _register_customer("invalida.links")

    client.post(FORGOT_URL, json={"email": cust["email"]})
    first_token = _token_from_url(captured_reset_urls[0]["url"])

    client.post(FORGOT_URL, json={"email": cust["email"]})
    second_token = _token_from_url(captured_reset_urls[1]["url"])

    # o link da primeira solicitação foi invalidado
    res = client.post(RESET_URL, json={"token": first_token, "password": "SenhaValida123"})
    assert res.status_code == 400

    # o link mais recente funciona
    res = client.post(RESET_URL, json={"token": second_token, "password": "SenhaValida123"})
    assert res.status_code == 200


def test_forgot_for_inactive_customer_sends_no_email(captured_reset_urls):
    cust = _register_customer("inativo")

    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == cust["email"]).first()
        customer.is_active = False
        db.commit()
    finally:
        db.close()

    res = client.post(FORGOT_URL, json={"email": cust["email"]})
    assert res.status_code == 200
    assert captured_reset_urls == []

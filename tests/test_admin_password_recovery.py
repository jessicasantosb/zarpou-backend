from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_SECRET_KEY, Settings, settings
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.core.two_factor import encrypt_totp_secret, generate_base32_secret, generate_totp_code
from app.features.bookings.infra.models import Booking
from app.models.user import User
from test_password_recovery import captured_reset_urls, client, _token_from_url


def test_production_rejects_default_signing_secret():
    with pytest.raises(ValidationError, match="Configure SECRET_KEY"):
        Settings(ENVIRONMENT="production", SECRET_KEY=DEFAULT_SECRET_KEY)


def test_legacy_admin_alias_never_creates_account():
    response = client.post("/api/v1/auth/login", json={"email": "admin", "password": "admin123"})
    assert response.status_code == 400


def test_admin_password_reset_is_single_use_and_separate_from_customer(captured_reset_urls, monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "notifications@example.com")
    email = f"admin-reset-{uuid4().hex}@exemplo.com"
    with SessionLocal() as db:
        db.add(User(name="Admin Teste", email=email, password_hash=get_password_hash("OrigemTeste123")))
        db.commit()

    base = "/api/v1/auth/admin/password"
    login = "/api/v1/auth/login"
    old_session = client.post(login, json={"email": email, "password": "OrigemTeste123"}).json()
    known = client.post(f"{base}/forgot", json={"email": email})
    unknown = client.post(f"{base}/forgot", json={"email": "ausente@exemplo.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    (sent,) = captured_reset_urls
    assert sent["email"] == email
    assert "/admin/redefinir-senha?" in sent["url"]
    payload = {"token": _token_from_url(sent["url"]), "password": "NovaSenhaTeste123"}
    assert client.post("/api/v1/auth/customer/password/reset", json=payload).status_code == 400
    start = Barrier(2)

    def submit_reset():
        start.wait(timeout=5)
        return client.post(f"{base}/reset", json=payload).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = (pool.submit(submit_reset) for _ in range(2))
        assert sorted([first.result(), second.result()]) == [200, 400]
    assert client.post(f"{base}/reset", json=payload).status_code == 400
    assert client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {old_session['access_token']}",
    }).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={
        "refresh_token": old_session["refresh_token"],
    }).status_code == 401
    assert client.post(login, json={"email": email, "password": "OrigemTeste123"}).status_code == 400
    assert client.post(login, json={"email": email, "password": payload["password"]}).status_code == 200


def test_admin_totp_requires_challenge_before_issuing_session():
    email = f"admin-mfa-{uuid4().hex}@exemplo.com"
    password = "SenhaTesteForte123"
    secret = generate_base32_secret()
    user_id = str(uuid4())
    booking_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(
            id=user_id, name="Admin Teste MFA", email=email, password_hash=get_password_hash(password),
            two_factor_enabled=True, two_factor_method="authenticator",
            two_factor_secret=encrypt_totp_secret(secret),
        ))
        db.add(Booking(
            id=booking_id, locator_code=f"ZRP-{uuid4().hex[:12].upper()}",
            product_type="hotel", payment_method="pix",
        ))
        db.commit()

    old_token = create_access_token(user_id, role="admin")
    booking_url = f"/api/v1/bookings/{booking_id}"
    assert client.get(booking_url, headers={"Authorization": f"Bearer {old_token}"}).status_code == 404

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    data = login.json()
    assert data.get("access_token") is None
    assert data.get("refresh_token") is None
    assert data["available_methods"] == ["authenticator"]

    verify = "/api/v1/auth/admin/2fa/verify"
    payload = {"challenge": data["challenge"], "method": "authenticator", "code": "invalid"}
    assert client.post(verify, json=payload).status_code == 400
    payload["code"] = generate_totp_code(secret)
    session = client.post(verify, json=payload)
    assert session.status_code == 200
    assert client.post(verify, json=payload).status_code == 400
    headers = {"Authorization": f"Bearer {session.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get(booking_url, headers=headers).status_code == 200


def test_admin_password_update_invalidates_outstanding_reset_link(captured_reset_urls, monkeypatch):
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(settings, "RESEND_FROM_EMAIL", "notifications@example.com")
    email = f"admin-password-{uuid4().hex}@exemplo.com"
    user_id = str(uuid4())
    with SessionLocal() as db:
        db.add(User(id=user_id, name="Admin Teste", email=email, password_hash=get_password_hash("SenhaTeste123")))
        db.commit()

    base = "/api/v1/auth/admin/password"
    assert client.post(f"{base}/forgot", json={"email": email}).status_code == 200
    (sent,) = captured_reset_urls

    administrator = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com", "password": "admin123",
    })
    headers = {"Authorization": f"Bearer {administrator.json()['access_token']}"}
    assert client.put(f"/api/v1/users/{user_id}", headers=headers, json={"password": "SegundaSenha123"}).status_code == 200

    reset_with_old_link = client.post(f"{base}/reset", json={
        "token": _token_from_url(sent["url"]), "password": "TerceiraSenha123",
    })
    assert reset_with_old_link.status_code == 400

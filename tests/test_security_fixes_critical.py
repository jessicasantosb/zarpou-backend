"""
Testes das correções das falhas críticas de segurança (auditoria 2026-10-17):

1. Login de cliente SEM senha é proibido — a senha é obrigatória e sempre verificada
   (toda conta criada nasce com senha; contas legadas sem senha definem senha no
   primeiro acesso autenticado).
2. Escada de privilégio bloqueada — um gestor não-admin (mesmo com a tela
   'administradores') não pode alterar contas de Administrador Geral, nem
   auto-conceder/conceder telas que ele mesmo não possui.
3. Segredos 2FA de administradores não vazam em respostas (login, /me, /users,
   /me/2fa) e são cifrados em repouso (Fernet).
"""
import time

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import create_access_token, verify_password
from app.main import app
from app.models.customer import Customer
from app.models.user import User

client = TestClient(app)

ADMIN_EMAIL = "admin@zarpou.com.br"
ADMIN_PASSWORD = "admin123"
TEAM_PASSWORD = "SenhaEquipe123"


def _admin_headers():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        assert admin is not None
        token = create_access_token(subject=admin.id, role=admin.role)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def _create_team_user(headers, name, email, screens, role="personalizado"):
    res = client.post(
        "/api/v1/users",
        json={
            "name": name,
            "email": email,
            "password": TEAM_PASSWORD,
            "role": role,
            "allowedScreens": screens,
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


def _login(email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Crítico 1 — login de cliente sem senha é proibido
# ---------------------------------------------------------------------------

def test_customer_login_without_password_is_rejected():
    res = client.post("/api/v1/auth/customer/login", json={"email": "sem.senha.teste@exemplo.com"})
    assert res.status_code == 422  # schema exige password


def test_customer_register_without_password_is_rejected():
    res = client.post(
        "/api/v1/auth/customer/register",
        json={"name": "Sem Senha", "email": "registro.sem.senha@exemplo.com"},
    )
    assert res.status_code == 422


def test_customer_login_wrong_password_is_rejected():
    ts = int(time.time() * 1000)
    email = f"senha.errada.{ts}@exemplo.com"
    reg = client.post(
        "/api/v1/auth/customer/register",
        json={"name": "Teste Senha", "email": email, "password": "senhaCorreta123"},
    )
    assert reg.status_code == 201

    res = client.post(
        "/api/v1/auth/customer/login",
        json={"email": email, "password": "senhaErrada999"},
    )
    assert res.status_code == 400
    assert "access_token" not in res.json()


def test_customer_login_correct_password_works():
    ts = int(time.time() * 1000)
    email = f"senha.certa.{ts}@exemplo.com"
    pwd = "senhaCorreta123"
    reg = client.post(
        "/api/v1/auth/customer/register",
        json={"name": "Teste Senha OK", "email": email, "password": pwd},
    )
    assert reg.status_code == 201

    res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": pwd})
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_unknown_email_login_does_not_create_account():
    """Sem auto-criação no login (SECURITY_BACKLOG #1): é preciso cadastro prévio."""
    ts = int(time.time() * 1000)
    email = f"auto.criado.{ts}@exemplo.com"
    res = client.post(
        "/api/v1/auth/customer/login",
        json={"email": email, "password": "minhaSenha123"},
    )
    assert res.status_code == 400
    assert "access_token" not in res.json()

    db = SessionLocal()
    try:
        # o login nunca cria conta
        assert db.query(Customer).filter(Customer.email == email).first() is None
    finally:
        db.close()


def test_unknown_email_login_response_equals_wrong_password_response():
    """Sem oráculo de enumeração: e-mail desconhecido responde igual a senha errada."""
    ts = int(time.time() * 1000)
    email = f"enum.login.{ts}@exemplo.com"
    reg = client.post(
        "/api/v1/auth/customer/register",
        json={"name": "Teste Enum Login", "email": email, "password": "senhaCorreta123"},
    )
    assert reg.status_code == 201

    res_unknown = client.post(
        "/api/v1/auth/customer/login",
        json={"email": f"nunca.cadastrado.{ts}@exemplo.com", "password": "minhaSenha123"},
    )
    res_wrong_password = client.post(
        "/api/v1/auth/customer/login",
        json={"email": email, "password": "senhaErrada999"},
    )
    assert res_unknown.status_code == res_wrong_password.status_code == 400
    assert res_unknown.json() == res_wrong_password.json()


def test_legacy_account_without_password_sets_password_on_first_login():
    """Conta legada criada sem senha (bug antigo) define senha no 1º acesso."""
    ts = int(time.time() * 1000)
    email = f"legada.sem.senha.{ts}@exemplo.com"
    db = SessionLocal()
    try:
        legacy = Customer(id=f"cust-legada-{ts}", name="Legada", email=email, is_active=True)
        legacy.password_hash = None
        db.add(legacy)
        db.commit()
    finally:
        db.close()

    # senha fraca não é aceita para definir a senha da conta
    res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": "abc"})
    assert res.status_code == 400

    # senha válida define a senha e autentica
    res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": "NovaSenha123"})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        cust = db.query(Customer).filter(Customer.email == email).first()
        assert cust.password_hash
        assert verify_password("NovaSenha123", cust.password_hash)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Crítico 2 — escada de privilégio bloqueada
# ---------------------------------------------------------------------------

def _superadmin_id():
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == ADMIN_EMAIL).first().id
    finally:
        db.close()


def test_non_admin_cannot_modify_superadmin():
    ts = int(time.time() * 1000)
    email = f"gestor.escada.{ts}@teste.com"
    _create_team_user(_admin_headers(), "Gestor Escada", email, ["administradores"])
    headers = _login(email, TEAM_PASSWORD)

    admin_id = _superadmin_id()

    # trocar a senha do superadmin → 403
    res = client.put(
        f"/api/v1/users/{admin_id}",
        json={"password": "Hackeada123"},
        headers=headers,
    )
    assert res.status_code == 403

    # desativar o superadmin → 403
    res = client.patch(
        f"/api/v1/users/{admin_id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert res.status_code == 403

    # deletar o superadmin → 403
    res = client.delete(f"/api/v1/users/{admin_id}", headers=headers)
    assert res.status_code == 403

    # superadmin permanece intacto
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.id == admin_id).first()
        assert admin.is_active is True
        assert admin.role == "admin"
        assert verify_password(ADMIN_PASSWORD, admin.password_hash)
    finally:
        db.close()


def test_non_admin_cannot_change_own_role():
    ts = int(time.time() * 1000)
    email = f"gestor.proprio.{ts}@teste.com"
    uid = _create_team_user(_admin_headers(), "Gestor Proprio", email, ["administradores"])
    headers = _login(email, TEAM_PASSWORD)

    res = client.put(f"/api/v1/users/{uid}", json={"role": "admin"}, headers=headers)
    assert res.status_code == 403

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        assert user.role == "personalizado"
    finally:
        db.close()


def test_non_admin_cannot_self_escalate_screens():
    ts = int(time.time() * 1000)
    email = f"gestor.autotelas.{ts}@teste.com"
    uid = _create_team_user(_admin_headers(), "Gestor AutoTelas", email, ["administradores"])
    headers = _login(email, TEAM_PASSWORD)

    res = client.put(
        f"/api/v1/users/{uid}",
        json={"allowedScreens": ["administradores", "configuracoes"]},
        headers=headers,
    )
    assert res.status_code == 403

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        assert user.allowed_screens == ["administradores"]
    finally:
        db.close()


def test_non_admin_cannot_grant_unowned_screens():
    ts = int(time.time() * 1000)
    headers_admin = _admin_headers()

    target_email = f"alvo.telass.{ts}@teste.com"
    target_id = _create_team_user(headers_admin, "Alvo Telas", target_email, ["dashboard"])

    grantor_email = f"gestor.concede.{ts}@teste.com"
    _create_team_user(headers_admin, "Gestor Concede", grantor_email, ["administradores"])
    headers = _login(grantor_email, TEAM_PASSWORD)

    # não pode conceder 'configuracoes' (não a possui) → 403
    res = client.put(
        f"/api/v1/users/{target_id}",
        json={"allowedScreens": ["configuracoes"]},
        headers=headers,
    )
    assert res.status_code == 403

    # pode conceder telas que possui ('administradores') → 200
    res = client.put(
        f"/api/v1/users/{target_id}",
        json={"allowedScreens": ["administradores"]},
        headers=headers,
    )
    assert res.status_code == 200


def test_non_admin_cannot_create_user_with_unowned_screens():
    ts = int(time.time() * 1000)
    email = f"gestor.cria.{ts}@teste.com"
    _create_team_user(_admin_headers(), "Gestor Cria", email, ["administradores"])
    headers = _login(email, TEAM_PASSWORD)

    res = client.post(
        "/api/v1/users",
        json={
            "name": "Filho Escada",
            "email": f"filho.escada.{ts}@teste.com",
            "password": TEAM_PASSWORD,
            "role": "personalizado",
            "allowedScreens": ["configuracoes"],
        },
        headers=headers,
    )
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Crítico 3 — segredos 2FA de administradores não vazam e são cifrados em repouso
# ---------------------------------------------------------------------------

def test_admin_2fa_secrets_not_exposed_in_users_list():
    res = client.get("/api/v1/users", headers=_admin_headers())
    assert res.status_code == 200
    for item in res.json():
        assert "twoFactorSecret" not in item
        assert "two_factor_secret" not in item
        assert "backupCodes" not in item
        assert "backup_codes" not in item


def test_admin_2fa_secrets_not_exposed_in_login_and_me():
    res = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert res.status_code == 200
    user_payload = res.json()["user"]
    assert "twoFactorSecret" not in user_payload
    assert "backupCodes" not in user_payload

    res = client.get("/api/v1/auth/me", headers=_admin_headers())
    assert res.status_code == 200
    me = res.json()
    assert "twoFactorSecret" not in me
    assert "backupCodes" not in me


def test_admin_totp_secret_encrypted_at_rest():
    ts = int(time.time() * 1000)
    email = f"admin.2fa.{ts}@teste.com"
    uid = _create_team_user(
        _admin_headers(), "Admin 2FA", email, ["administradores"]
    )
    headers = _login(email, TEAM_PASSWORD)

    secret = "JBSWY3DPEHPK3PXP"
    res = client.patch(
        "/api/v1/auth/me/2fa",
        json={"enabled": True, "method": "app", "secret": secret},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    # resposta não devolve segredos
    assert "twoFactorSecret" not in body
    assert "backupCodes" not in body

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        # segredo cifrado em repouso (Fernet, prefixo 'enc:'), nunca texto puro
        assert user.two_factor_secret is not None
        assert user.two_factor_secret.startswith("enc:")
        assert secret not in user.two_factor_secret
    finally:
        db.close()

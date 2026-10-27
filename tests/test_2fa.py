import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.two_factor import generate_totp_code

client = TestClient(app)


def test_2fa_full_lifecycle():
    # 1. Registrar / Logar cliente com email idempotente
    email = f"cliente.2fa.{int(time.time())}@exemplo.com"
    pwd = "minhaSenhaSegura123"
    reg_res = client.post(
        "/api/v1/auth/customer/register",
        json={"name": "Cliente 2FA", "email": email, "password": pwd},
    )
    assert reg_res.status_code in (201, 400)  # 400 = já cadastrado em execução anterior

    login_res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Consultar status inicial de 2FA (deve estar desativado)
    status_res = client.get("/api/v1/auth/customer/2fa", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["enabled"] is False

    # 3. Ativar 2FA com app autenticador e códigos reserva
    secret = "JBSWY3DPEHPK3PXP"
    backups = ["A1B2-C3D4", "E5F6-G7H8", "I9J0-K1L2"]
    enable_res = client.patch(
        "/api/v1/auth/customer/2fa",
        headers=headers,
        json={
            "enabled": True,
            "method": "authenticator",
            "secret": secret,
            "backupCodes": backups,
        },
    )
    assert enable_res.status_code == 200
    enabled_data = enable_res.json()
    assert enabled_data["enabled"] is True
    assert enabled_data["method"] == "authenticator"
    assert enabled_data["secret"] == secret
    assert enabled_data["backupCodesCount"] == 3

    # 4. Verificar login com 2FA ativado (campo twoFactorEnabled == True)
    login2_res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": pwd})
    assert login2_res.status_code == 200
    user_info = login2_res.json()["user"]
    assert user_info["twoFactorEnabled"] is True
    assert user_info["twoFactorMethod"] == "authenticator"

    # 5. Validar verificação via código TOTP
    current_totp = generate_totp_code(secret)
    verify_res = client.post(
        "/api/v1/auth/customer/2fa/verify",
        json={"email": email, "code": current_totp},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["access_token"] is not None

    # 6. Validar verificação via Backup Code descartável
    backup_code = backups[0]
    verify_backup_res = client.post(
        "/api/v1/auth/customer/2fa/verify",
        json={"email": email, "code": backup_code},
    )
    assert verify_backup_res.status_code == 200

    # Conferir se o código de backup utilizado foi consumido
    status_after_backup = client.get("/api/v1/auth/customer/2fa", headers=headers)
    assert status_after_backup.status_code == 200
    assert backup_code not in status_after_backup.json()["backupCodes"]
    assert status_after_backup.json()["backupCodesCount"] == 2

    # 7. Solicitar envio de código por e-mail e validar
    send_code_res = client.post(
        "/api/v1/auth/customer/2fa/send-code",
        headers=headers,
    )
    assert send_code_res.status_code == 200
    send_code_body = send_code_res.json()
    assert send_code_body["success"] is True
    # Regressão de segurança: o código gerado jamais pode ecoar na resposta
    # (o cliente só deve recebê-lo pelo e-mail).
    assert "code" not in send_code_body

    # 8. Alteração de senha do cliente
    change_pwd_res = client.post(
        "/api/v1/auth/customer/change-password",
        headers=headers,
        json={"currentPassword": pwd, "newPassword": "novaSenhaSegura456"},
    )
    assert change_pwd_res.status_code == 200
    assert change_pwd_res.json()["success"] is True

    # 9. Desativar 2FA
    disable_res = client.patch(
        "/api/v1/auth/customer/2fa",
        headers=headers,
        json={"enabled": False},
    )
    assert disable_res.status_code == 200
    assert disable_res.json()["enabled"] is False

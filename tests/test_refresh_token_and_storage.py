import io
import time
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, create_refresh_token
from app.core.database import SessionLocal
from app.models.user import User
from app.models.customer import Customer
from app.models.company import Company
from app.features.storage.infra.storage_providers import S3StorageProvider

client = TestClient(app)


def test_admin_login_returns_refresh_token_and_can_refresh():
    # 1. Login com admin existente
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@zarpou.com.br", "password": "admin123"},
    )
    assert login_res.status_code == 200, login_res.text
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    refresh_token = data["refresh_token"]

    # 2. Utilizar o refresh token para renovar as credenciais
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200, refresh_res.text
    new_data = refresh_res.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert new_data["token_type"] == "bearer"

    # 3. Testar acesso a rota protegida com o novo access_token
    auth_headers = {"Authorization": f"Bearer {new_data['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "admin@zarpou.com.br"


def test_customer_login_returns_refresh_token_and_can_refresh():
    # 1. Login com cliente
    email = f"refresh.test.{int(time.time())}@exemplo.com"
    pwd = "minhaSenhaSegura123"
    login_res = client.post("/api/v1/auth/customer/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    refresh_token = data["refresh_token"]

    # 2. Renovar via /auth/refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data

    # 3. Testar rota protegida com novo access_token
    auth_headers = {"Authorization": f"Bearer {new_data['access_token']}"}
    me_res = client.get("/api/v1/auth/customer/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_company_b2b_login_returns_refresh_token_and_can_refresh():
    # 1. Login ou cadastro de empresa B2B
    cnpj = f"{int(time.time())}"[:14].zfill(14)
    email = f"corp.{int(time.time())}@techcorp.com"
    reg_res = client.post(
        "/api/v1/companies/register",
        json={
            "razaoSocial": "Tech Corp Viagens SA",
            "nomeFantasia": "Tech Corp",
            "cnpj": cnpj,
            "corporateEmail": email,
            "phone": "11988887777",
            "managerName": "Carlos Diretor",
            "managerCpf": "12345678901",
            "password": "SenhaCorporativa123",
        },
    )
    assert reg_res.status_code == 201, reg_res.text

    # 2. Login da empresa
    login_res = client.post(
        "/api/v1/companies/login",
        json={"login": email, "password": "SenhaCorporativa123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    company_refresh_token = login_data["refresh_token"]

    # 3. Renovar token da empresa via /auth/refresh
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": company_refresh_token},
    )
    assert refresh_res.status_code == 200
    refreshed = refresh_res.json()
    assert "access_token" in refreshed
    assert "refresh_token" in refreshed
    assert refreshed["user"]["role"] == "company"



def test_invalid_refresh_token_rejected():
    # Enviar token inválido / adulterado
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": "token_invalido_xyz"})
    assert res.status_code == 401
    assert "inválido" in res.json()["detail"].lower() or "expirado" in res.json()["detail"].lower()

    # Enviar access token no lugar de refresh token (deve ser rejeitado pois tipo != refresh)
    access_token = create_access_token(subject="123", role="admin")
    res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert res2.status_code == 401
    assert "inválido" in res2.json()["detail"].lower()


def test_storage_upload_validation_and_local_fallback():
    # 1. Upload de arquivo com tipo inválido (ex: texto simples)
    invalid_file = io.BytesIO(b"conteudo de texto nao permitido")
    res_invalid = client.post(
        "/api/v1/storage/upload?folder=banners",
        files={"file": ("arquivo.txt", invalid_file, "text/plain")},
    )
    assert res_invalid.status_code == 400
    assert "não suportado" in res_invalid.json()["detail"].lower()

    # 2. Upload de imagem válida (PNG)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    valid_file = io.BytesIO(png_bytes)
    res_upload = client.post(
        "/api/v1/storage/upload?folder=promocoes",
        files={"file": ("banner-promo.png", valid_file, "image/png")},
    )
    assert res_upload.status_code == 200, res_upload.text
    data = res_upload.json()
    assert data["success"] is True
    assert "url" in data
    assert data["filename"].endswith(".png")
    assert data["folder"] == "promocoes"
    assert data["size"] == len(png_bytes)
    assert data["contentType"] == "image/png"
    assert data["provider"] in ["aws_s3", "supabase", "local"]


def test_s3_storage_provider_upload():
    # Testa a classe S3StorageProvider com mock do boto3
    provider = S3StorageProvider(
        bucket_name="meu-bucket-aws",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="sa-east-1",
        public_url_prefix="https://cdn.zarpou.com.br",
    )

    fake_content = b"\x89PNG\r\n\x1a\nfakecontent"
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        result = asyncio.run(
            provider.upload(
                content=fake_content,
                filename="foto.png",
                content_type="image/png",
                folder="destinos",
            )
        )

        assert result.success is True
        assert result.provider == "aws_s3"
        assert result.url == "https://cdn.zarpou.com.br/destinos/foto.png"
        assert result.size == len(fake_content)
        assert result.filename == "foto.png"
        assert result.folder == "destinos"

        mock_s3.put_object.assert_called_once_with(
            Bucket="meu-bucket-aws",
            Key="destinos/foto.png",
            Body=fake_content,
            ContentType="image/png",
        )

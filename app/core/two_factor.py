import base64
import hashlib
import hmac
import json
import secrets
import string
import struct
import time
from typing import List, Optional
import httpx
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

# Gerador criptograficamente seguro (OWASP A02). Substitui o módulo `random`,
# que é previsível e inadequado para segredos TOTP, PINs e códigos de backup.
random = secrets.SystemRandom()


# Alfabeto RFC 4648 Base32
BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"

# Prefixo que identifica valores cifrados no banco (permite migrar dados legados em texto puro)
_ENC_PREFIX = "enc:"


def _fernet() -> Fernet:
    """Chave Fernet (AES-128-CBC + HMAC-SHA256) derivada do SECRET_KEY da aplicação."""
    key = hashlib.sha256(f"zarpou-totp::{settings.SECRET_KEY}".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_totp_secret(secret: Optional[str]) -> Optional[str]:
    """Cifra o segredo TOTP para armazenamento em repouso."""
    if not secret:
        return None
    if secret.startswith(_ENC_PREFIX):
        return secret
    return _ENC_PREFIX + _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(stored: Optional[str]) -> str:
    """Decifra o segredo TOTP. Valores legados (texto puro) são retornados como estão."""
    if not stored:
        return ""
    if not stored.startswith(_ENC_PREFIX):
        return stored
    try:
        return _fernet().decrypt(stored[len(_ENC_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def _normalize_backup_code(code: str) -> str:
    return code.strip().upper()


def hash_backup_code(code: str) -> str:
    """Hash HMAC-SHA256 (com pepper = SECRET_KEY) de um código de recuperação."""
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        _normalize_backup_code(code).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256:{digest}"


def find_backup_code_match(code: str, stored_codes: List[str]) -> Optional[str]:
    """
    Retorna o item armazenado que corresponde ao código informado (comparação em tempo constante),
    aceitando tanto hashes quanto códigos legados em texto puro.
    """
    candidate_hash = hash_backup_code(code)
    candidate_plain = _normalize_backup_code(code)
    for stored in stored_codes:
        target = candidate_hash if stored.startswith("sha256:") else candidate_plain
        if hmac.compare_digest(stored, target):
            return stored
    return None


def generate_base32_secret(length: int = 16) -> str:
    """Gera uma chave secreta Base32 para TOTP (Google Authenticator / Authy)."""
    return "".join(random.choice(BASE32_ALPHABET) for _ in range(length))


def generate_totp_code(secret: str, timestamp: Optional[float] = None) -> str:
    """
    Gera o código TOTP de 6 dígitos para o timestamp fornecido (padrão RFC 6238).
    Compatível 1:1 com Google Authenticator e Microsoft Authenticator.
    """
    if timestamp is None:
        timestamp = time.time()
    
    clean_secret = secret.strip().upper().replace(" ", "").rstrip("=")
    # Adiciona padding Base32 se necessário
    missing_padding = len(clean_secret) % 8
    if missing_padding:
        clean_secret += "=" * (8 - missing_padding)

    secret_bytes = base64.b32decode(clean_secret)
    epoch_interval = int(timestamp // 30)
    time_bytes = struct.pack(">Q", epoch_interval)

    digest = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    otp = code % 1000000
    return f"{otp:06d}"


def verify_totp_code(secret: str, token: str, window: int = 1) -> bool:
    """
    Valida código TOTP com tolerância de janela (±1 passo de 30s) para contornar relógios dessincronizados.
    """
    clean_token = "".join(c for c in token if c.isdigit())
    if len(clean_token) != 6:
        return False

    now = time.time()
    for w in range(-window, window + 1):
        expected = generate_totp_code(secret, now + (w * 30))
        if hmac.compare_digest(expected, clean_token):
            return True
    return False


def generate_backup_codes(count: int = 5) -> List[str]:
    """Gera códigos de recuperação descartáveis (Backup Codes) no formato XXXX-XXXX."""
    chars = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    codes = []
    for _ in range(count):
        part1 = "".join(random.choice(chars) for _ in range(4))
        part2 = "".join(random.choice(chars) for _ in range(4))
        codes.append(f"{part1}-{part2}")
    return codes


def generate_email_code() -> str:
    """Gera código numérico de 6 dígitos para verificação por e-mail."""
    return f"{random.randint(100000, 999999):06d}"


def send_2fa_email_code(name: str, email: str, code: str) -> bool:
    """
    Dispara o e-mail contendo o código de segurança 2FA para o cliente via Resend.
    """
    api_key = settings.RESEND_API_KEY
    if not api_key:
        print(f"[2FA DEV SIMULATION] Código para {email}: {code}")
        return True

    try:
        first_name = name.split()[0] if name else "Viajante"
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 540px; margin: 0 auto; padding: 25px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff;">
          <div style="background-color: #003366; padding: 25px; text-align: center; border-radius: 14px;">
            <h1 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 0.5px;">Zarpou Viagens e Turismo</h1>
            <p style="color: #f7a01d; margin: 6px 0 0 0; font-size: 13px; font-weight: bold; text-transform: uppercase;">Código de Verificação de Segurança (2FA)</p>
          </div>
          <div style="padding: 30px 20px; color: #334155; line-height: 1.6;">
            <p style="font-size: 15px;">Olá, <strong>{first_name}</strong>!</p>
            <p style="font-size: 14px; color: #64748b;">Recebemos uma solicitação de autenticação na sua conta Zarpou. Utilize o código de 6 dígitos abaixo para concluir o acesso:</p>
            
            <div style="text-align: center; margin: 28px 0;">
              <span style="display: inline-block; background-color: #f8fafc; border: 2px dashed #003366; padding: 14px 28px; font-size: 32px; font-family: 'Courier New', monospace; font-weight: 900; letter-spacing: 8px; color: #003366; border-radius: 12px;">
                {code}
              </span>
            </div>

            <p style="font-size: 12px; color: #64748b; text-align: center;">Este código é válido por <strong>10 minutos</strong>. Se você não solicitou este acesso, proteja sua conta alterando sua senha imediatamente.</p>
            
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 25px 0;" />
            <p style="font-size: 11px; color: #94a3b8; text-align: center; margin: 0;">
              Zarpou Viagens e Turismo Ltda • Cadastur: 34.120.948/0001-90<br />
              Mensagem automática enviada pelo sistema de segurança Zarpou.
            </p>
          </div>
        </div>
        """
        with httpx.Client(timeout=10.0) as client:
            res = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": "Zarpou Segurança <lazer@zarpouviagens.com.br>",
                    "to": [email],
                    "subject": f"🔐 Seu código de segurança Zarpou: {code}",
                    "html": html_content,
                },
            )
            return res.status_code in [200, 201]
    except Exception as exc:
        print("[2FA Resend Error]", exc)
        return False

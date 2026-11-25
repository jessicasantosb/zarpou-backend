import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Optional
import bcrypt
import jwt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    role: str = "customer",
    expires_delta: Optional[timedelta] = None,
    *,
    mfa_verified: bool = False,
    session_version: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode = {
        "exp": expire,
        "iat": int(now.timestamp()),
        "issued_at_us": int(now.timestamp() * 1_000_000),
        "sub": str(subject),
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
    }
    if mfa_verified:
        to_encode["mfa_verified"] = True
    if session_version is not None:
        to_encode["session_version"] = session_version
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token_any(token: str) -> Optional[dict]:
    """Decodifica e valida assinatura/expiração de qualquer token (access ou refresh)."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    decoded = decode_token_any(token)
    # Refresh tokens nunca podem ser usados como credencial de acesso às rotas
    if not decoded or decoded.get("type") == "refresh":
        return None
    return decoded


def create_refresh_token(
    subject: Union[str, Any],
    role: str = "customer",
    expires_delta: Optional[timedelta] = None,
    *,
    mfa_verified: bool = False,
    session_version: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))

    to_encode = {
        "exp": expire,
        "iat": int(now.timestamp()),
        "issued_at_us": int(now.timestamp() * 1_000_000),
        "sub": str(subject),
        "role": role,
        "type": "refresh",
        "jti": uuid.uuid4().hex,
    }
    if mfa_verified:
        to_encode["mfa_verified"] = True
    if session_version is not None:
        to_encode["session_version"] = session_version
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if decoded.get("type") != "refresh":
            return None
        return decoded
    except Exception:
        return None


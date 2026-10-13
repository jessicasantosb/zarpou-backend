"""
Blacklist de tokens JWT revogados (logout imediato / OWASP A07).

Cada token emitido possui um identificador único (`jti`). Ao fazer logout, o `jti`
é gravado nesta tabela até a expiração natural do token, impedindo seu reuso.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import decode_token_any


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True, index=True)
    subject = Column(String(100), nullable=True)
    token_type = Column(String(20), nullable=False, default="access")
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


def is_token_revoked(db: Session, jti: Optional[str]) -> bool:
    if not jti:
        # Tokens legados sem jti não podem ser revogados individualmente; aceitos até expirarem.
        return False
    return db.query(RevokedToken.jti).filter(RevokedToken.jti == jti).first() is not None


def revoke_token(db: Session, raw_token: str) -> bool:
    """Revoga um token (access ou refresh). Retorna True se o token era válido."""
    payload = decode_token_any(raw_token)
    if not payload or not payload.get("jti"):
        return False

    jti = payload["jti"]
    if is_token_revoked(db, jti):
        return True

    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc)
    db.add(RevokedToken(
        jti=jti,
        subject=str(payload.get("sub")),
        token_type=payload.get("type", "access"),
        expires_at=expires_at,
    ))
    _purge_expired(db)
    db.commit()
    return True


def _purge_expired(db: Session) -> None:
    """Remove entradas cujo token já expirou naturalmente (mantém a tabela enxuta)."""
    db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete(
        synchronize_session=False
    )

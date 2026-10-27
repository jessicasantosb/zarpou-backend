"""
Blacklist de tokens JWT revogados (logout imediato / OWASP A07).

Cada token emitido possui um identificador único (`jti`). Ao fazer logout, o `jti`
é gravado nesta tabela até a expiração natural do token, impedindo seu reuso.

Além disso, `revoke_subject_tokens` grava um **marcador de subject** (`sub:<id>`):
a partir dele, qualquer token (access ou refresh) emitido ANTES da marca deixa de
ser aceito, enquanto tokens emitidos depois (novo login) continuam válidos. É o
mecanismo usado no reset de senha para derrubar sessões comprometidas sem precisar
conhecer os `jti` emitidos (SECURITY_BACKLOG #2).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base
from app.core.security import decode_token_any


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti = Column(String(64), primary_key=True, index=True)
    subject = Column(String(100), nullable=True)
    token_type = Column(String(20), nullable=False, default="access")
    revoked_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


def is_token_revoked(
    db: Session,
    jti: Optional[str],
    subject: Optional[str] = None,
    issued_at: Optional[int] = None,
) -> bool:
    """
    Verifica se um token está revogado.

    - Revogação individual: o `jti` está na tabela (logout).
    - Revogação por subject: existe o marcador `sub:<subject>` e o token foi
      emitido ANTES da marca (reset de senha derruba a sessão comprometida).
      Tokens sem `iat` (emitidos antes desta correção) não podem ser datados e
      são tratados como revogados quando existe marcador — falha fechada.
    """
    if jti and db.query(RevokedToken.jti).filter(RevokedToken.jti == jti).first() is not None:
        return True

    if subject is None:
        return False

    marker = db.query(RevokedToken).filter(RevokedToken.jti == f"sub:{subject}").first()
    if marker is None:
        return False
    if issued_at is None:
        return True

    issued = datetime.fromtimestamp(int(issued_at), tz=timezone.utc)
    revoked_at = (
        marker.revoked_at
        if marker.revoked_at.tzinfo
        else marker.revoked_at.replace(tzinfo=timezone.utc)
    )
    # `iat` tem precisão de segundos: um token emitido no mesmo segundo do reset
    # é considerado novo (evita 401 imediato no auto-login pós-reset).
    return issued < revoked_at.replace(microsecond=0)


def revoke_subject_tokens(db: Session, subject: str) -> None:
    """
    Marca todos os tokens já emitidos para `subject` como revogados (access e
    refresh). Tokens emitidos depois (novo login) permanecem válidos.
    Usado no reset de senha para derrubar sessões comprometidas (SECURITY_BACKLOG #2).
    """
    if not subject:
        return

    now = datetime.now(timezone.utc)
    marker_jti = f"sub:{subject}"
    # A marca precisa sobreviver à vida útil do refresh token mais longo já emitido.
    expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    existing = db.query(RevokedToken).filter(RevokedToken.jti == marker_jti).first()
    if existing:
        existing.revoked_at = now
        existing.expires_at = expires_at
    else:
        db.add(RevokedToken(
            jti=marker_jti,
            subject=subject,
            token_type="subject",
            revoked_at=now,
            expires_at=expires_at,
        ))
    _purge_expired(db)
    db.commit()


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

from datetime import datetime, timezone
import json
import uuid
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, Date, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    cpf = Column(String(20), nullable=True, index=True)
    birth_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Preferências de Notificação de Promoções & Novidades (WhatsApp e E-mail)
    notification_whatsapp_promotions = Column(Boolean, nullable=False, default=True)
    notification_email_promotions = Column(Boolean, nullable=False, default=True)
    notification_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Autenticação em Duas Etapas (2FA)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    two_factor_method = Column(String(20), nullable=True, default="email")
    two_factor_secret = Column(String(255), nullable=True)
    two_factor_backup_codes = Column(Text, nullable=True)
    two_factor_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    two_factor_temp_code = Column(String(10), nullable=True)
    two_factor_temp_code_expires_at = Column(DateTime(timezone=True), nullable=True)

    # LGPD - Registro de consentimento (Art. 7º I / Art. 8º) e anonimização (Art. 18 IV/VI)
    accepted_privacy_policy = Column(Boolean, nullable=False, default=False)
    accepted_terms_of_use = Column(Boolean, nullable=False, default=False)
    consent_version = Column(String(20), nullable=True)
    consent_at = Column(DateTime(timezone=True), nullable=True)
    consent_ip = Column(String(64), nullable=True)
    anonymized_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    bookings = relationship("Booking", back_populates="customer")

    @property
    def fullName(self) -> str:
        return self.name

    @property
    def notifications(self) -> dict:
        return {
            "whatsappPromotions": bool(self.notification_whatsapp_promotions),
            "emailPromotions": bool(self.notification_email_promotions),
            "updatedAt": self.notification_updated_at.isoformat() if self.notification_updated_at else None,
        }

    @property
    def twoFactorEnabled(self) -> bool:
        return bool(self.two_factor_enabled)

    @property
    def twoFactorMethod(self) -> str:
        return self.two_factor_method or "email"

    @property
    def twoFactorSecret(self) -> str:
        """Segredo TOTP decifrado (no banco fica cifrado com Fernet)."""
        from app.core.two_factor import decrypt_totp_secret
        return decrypt_totp_secret(self.two_factor_secret)

    @property
    def backupCodeHashes(self) -> list:
        """Lista armazenada de códigos de recuperação (hashes SHA-256; legados podem estar em texto)."""
        if not self.two_factor_backup_codes:
            return []
        try:
            return json.loads(self.two_factor_backup_codes)
        except Exception:
            return [c.strip() for c in self.two_factor_backup_codes.split(",") if c.strip()]

    @property
    def backupCodes(self) -> list:
        """
        Códigos de recuperação nunca são devolvidos após o cadastro (são armazenados como hash).
        Mantido por compatibilidade com o contrato da API; use `backupCodesCount`.
        """
        return []

    @property
    def consent(self) -> dict:
        return {
            "acceptedPrivacyPolicy": bool(self.accepted_privacy_policy),
            "acceptedTermsOfUse": bool(self.accepted_terms_of_use),
            "version": self.consent_version,
            "acceptedAt": self.consent_at.isoformat() if self.consent_at else None,
        }

    @property
    def twoFactorConfirmedAt(self) -> Optional[str]:
        return self.two_factor_confirmed_at.isoformat() if self.two_factor_confirmed_at else None


CustomerModel = Customer

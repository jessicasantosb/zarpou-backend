from datetime import datetime, timezone
import json
import uuid
from typing import List
from sqlalchemy import Column, String, Boolean, DateTime, Text
from app.core.database import Base

ALL_ADMIN_SCREENS = [
    "dashboard",
    "hero",
    "promocoes",
    "hospedagens",
    "passagens",
    "destinos",
    "reservas",
    "usuarios",
    "administradores",
    "configuracoes",
]


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    allowed_screens_raw = Column("allowed_screens", Text, nullable=True, default="[]")
    is_active = Column(Boolean, nullable=False, default=True)
    two_factor_enabled = Column(Boolean, nullable=False, default=False)
    two_factor_method = Column(String(20), nullable=True, default="email")
    two_factor_secret = Column(String(64), nullable=True)
    two_factor_backup_codes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    @property
    def twoFactorEnabled(self) -> bool:
        return bool(self.two_factor_enabled)

    @property
    def twoFactorMethod(self) -> Optional[str]:
        return self.two_factor_method

    @property
    def twoFactorSecret(self) -> Optional[str]:
        return self.two_factor_secret

    @property
    def backupCodes(self) -> List[str]:
        if not self.two_factor_backup_codes:
            return []
        try:
            val = json.loads(self.two_factor_backup_codes)
            return val if isinstance(val, list) else []
        except Exception:
            return []

    @property
    def allowedScreens(self) -> List[str]:
        # Superadministrador possui acesso irrestrito a todas as telas
        if self.role == "admin":
            return list(ALL_ADMIN_SCREENS)
        if not self.allowed_screens_raw:
            return []
        try:
            val = json.loads(self.allowed_screens_raw)
            return val if isinstance(val, list) else []
        except Exception:
            return []

    @property
    def allowed_screens(self) -> List[str]:
        return self.allowedScreens

    @allowed_screens.setter
    def allowed_screens(self, value):
        if isinstance(value, list):
            self.allowed_screens_raw = json.dumps(value)
        elif isinstance(value, str):
            self.allowed_screens_raw = value
        else:
            self.allowed_screens_raw = "[]"

    @property
    def screens(self) -> List[str]:
        return self.allowedScreens


UserModel = User

from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "fly-promo-development-only-change-before-deploy"
LEGACY_DEFAULT_SECRET_KEY = "zarpou_super_secret_jwt_key_change_in_production_xyz123"


def _local_database_url() -> str:
    database = Path("fly-promo.db")
    legacy_database = Path("zarpou.db")
    if not database.is_file() and legacy_database.is_file():
        database = legacy_database
    return f"sqlite:///./{database.name}"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Fly Promo API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="after")
    @classmethod
    def check_debug_in_production(cls, v: bool, info) -> bool:
        env = info.data.get("ENVIRONMENT", "development")
        if env.strip().lower() == "production":
            return False
        return v

    # Database
    DATABASE_URL: str = Field(default_factory=_local_database_url)
    SCHEMA_MIGRATIONS_ON_STARTUP: bool = True

    # Security & JWT
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # Rate Limiting (OWASP A04/A07) - pode ser desativado em testes automatizados
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URI: str = ""

    # Celery / Redis (fila de processamento em background, ex.: importações em massa)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""  # vazio => REDIS_URL
    CELERY_RESULT_BACKEND: str = ""  # vazio => REDIS_URL

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8008",
        "http://127.0.0.1:8008",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Integrations
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    CONTACT_EMAIL: str = ""
    PRIVACY_EMAIL: str = ""
    # Base do site usado nos links enviados por e-mail (ex.: recuperação de senha)
    FRONTEND_URL: str = "http://localhost:3000"
    AI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    MERCADOPAGO_ACCESS_TOKEN: str = ""
    # Supabase Storage
    SUPABASE_URL: str = "https://sipcctuvsscknwcpddmp.supabase.co"
    SUPABASE_KEY: str = "sb_publishable_Ju4HnfqSr0xmySuClniEKg_1m9cZlAJ"
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_BUCKET: str = "zarpou-media"

    # AWS S3 Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "sa-east-1"
    AWS_S3_BUCKET: str = ""
    AWS_S3_ENDPOINT_URL: str = ""
    AWS_S3_PUBLIC_URL_PREFIX: str = ""

    @property
    def resend_email_configured(self) -> bool:
        return bool(self.RESEND_API_KEY and self.RESEND_FROM_EMAIL)

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        secret = self.SECRET_KEY.strip()
        if self.ENVIRONMENT.strip().lower() == "production" and (
            secret in {DEFAULT_SECRET_KEY, LEGACY_DEFAULT_SECRET_KEY} or len(secret) < 32
        ):
            raise ValueError("Configure SECRET_KEY com um segredo exclusivo de produção de pelo menos 32 caracteres.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        hide_input_in_errors=True,
        extra="ignore"
    )


settings = Settings()

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.core.database import Base, engine
import app.models  # Carrega todos os modelos no Base.metadata
from app.api.router import api_router
from app.core.limiter import limiter


_STARTUP_COLUMN_MIGRATIONS = {
    "users": {
        "allowed_screens": "TEXT DEFAULT '[]'",
        "session_version": "INTEGER NOT NULL DEFAULT 0",
        "two_factor_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
        "two_factor_method": "VARCHAR(20) DEFAULT 'email'",
        "two_factor_secret": "VARCHAR(255)",
        "two_factor_backup_codes": "TEXT",
    },
    "admin_password_reset_tokens": {
        "session_version": "INTEGER NOT NULL DEFAULT -1",
    },
    "customers": {
        "accepted_privacy_policy": "BOOLEAN NOT NULL DEFAULT FALSE",
        "accepted_terms_of_use": "BOOLEAN NOT NULL DEFAULT FALSE",
        "consent_version": "VARCHAR(20)",
        "consent_at": "TIMESTAMP WITH TIME ZONE",
        "consent_ip": "VARCHAR(64)",
        "anonymized_at": "TIMESTAMP WITH TIME ZONE",
    },
    "coupons": {
        "notification_sent": "BOOLEAN NOT NULL DEFAULT FALSE",
        "notification_sent_at": "TIMESTAMP WITH TIME ZONE",
    },
    "bookings": {
        "coupon_code": "VARCHAR(50)",
    },
}


def _apply_column_migrations(conn: Connection | None = None) -> None:
    """Adiciona colunas novas em tabelas já existentes (create_all não altera tabelas)."""
    if conn is None:
        with engine.begin() as connection:
            _apply_column_migrations(connection)
        return

    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    for table, columns in _STARTUP_COLUMN_MIGRATIONS.items():
        if table not in existing_tables:
            continue
        current = {c["name"] for c in inspector.get_columns(table)}
        for column, ddl in columns.items():
            if column not in current:
                if conn.dialect.name == "sqlite":
                    ddl = ddl.replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

    # As chaves TOTP cifradas excedem o limite antigo de 64 caracteres.
    if "users" in existing_tables and conn.dialect.name == "postgresql":
        user_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("users")}
        if "64" in user_cols.get("two_factor_secret", ""):
            conn.execute(text("ALTER TABLE users ALTER COLUMN two_factor_secret TYPE VARCHAR(255)"))


def prepare_database_schema() -> None:
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(715608234)"))
        Base.metadata.create_all(bind=conn)
        _apply_column_migrations(conn)
        if conn.dialect.name == "postgresql":
            # Supabase can grant Data API roles access to newly created tables.
            tables = (
                "users, admin_login_challenges, admin_password_reset_tokens, "
                "location_countries, location_states, location_cities"
            )
            for table in tables.split(", "):
                conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(text(f"REVOKE ALL ON TABLE {tables} FROM PUBLIC"))
            roles = conn.execute(text(
                "SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')"
            )).scalars()
            for role in roles:
                conn.execute(text(f"REVOKE ALL ON TABLE {tables} FROM {role}"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.SCHEMA_MIGRATIONS_ON_STARTUP:
        prepare_database_schema()

    # Jobs de importação órfãos (servidor reiniciou no meio de uma carga)
    from app.core.database import SessionLocal
    from app.features.imports.app.services import recover_stale_jobs

    db = SessionLocal()
    try:
        recover_stale_jobs(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful de alta performance para a Fly Promo. "
                "Gerenciamento de hotéis, passagens aéreas, pacotes, reservas com emissão de PNR, "
                "checkout transparente, consultoria e concierge com IA.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configuração de Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware de Segurança: Injeção de Security Headers defensivos (OWASP A05)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# Configuração de CORS para permitir requisições do frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas da API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Servir uploads locais como fallback estático
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    return {"status": "healthy"}

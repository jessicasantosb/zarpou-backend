import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import Base, engine
import app.models  # Carrega todos os modelos no Base.metadata
from app.api.router import api_router
from app.core.limiter import limiter


_STARTUP_COLUMN_MIGRATIONS = {
    "users": {
        "allowed_screens": "TEXT DEFAULT '[]'",
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


def _apply_column_migrations() -> None:
    """Adiciona colunas novas em tabelas já existentes (create_all não altera tabelas)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in _STARTUP_COLUMN_MIGRATIONS.items():
            if table not in existing_tables:
                continue
            current = {c["name"] for c in inspector.get_columns(table)}
            for column, ddl in columns.items():
                if column not in current:
                    if engine.dialect.name == "sqlite":
                        ddl = ddl.replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))

        # Migração de tipo: o segredo TOTP dos administradores passou a ser cifrado
        # em repouso (Fernet, prefixo 'enc:'), que ocupa mais que o VARCHAR(64)
        # original. No SQLite a largura não é aplicada (affinity) — só o Postgres
        # precisa do ALTER (idempotente: só roda enquanto o tipo ainda for 64).
        if "users" in existing_tables and engine.dialect.name == "postgresql":
            user_cols = {c["name"]: str(c["type"]) for c in inspector.get_columns("users")}
            if "64" in user_cols.get("two_factor_secret", ""):
                conn.execute(text("ALTER TABLE users ALTER COLUMN two_factor_secret TYPE VARCHAR(255)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização: criar tabelas e migrações estruturais necessárias
    Base.metadata.create_all(bind=engine)
    _apply_column_migrations()

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
    description="API RESTful de alta performance para a Zarpou Viagens e Turismo. "
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

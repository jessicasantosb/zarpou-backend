import os

# Desativa o rate limiting global durante a suíte (os testes fazem muitos logins do mesmo IP).
# Os testes específicos de rate limit reativam o limiter explicitamente.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ensure_schema():
    """TestClient(app) sem context manager não executa o lifespan; garante tabelas/colunas novas."""
    import json
    from app.core.database import Base, engine, SessionLocal
    import app.models  # noqa: F401
    from app.main import _apply_column_migrations
    from app.core.security import get_password_hash
    from app.features.users.infra.models import User, ALL_ADMIN_SCREENS

    Base.metadata.create_all(bind=engine)
    _apply_column_migrations()

    # Garantir usuários de teste essenciais
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@zarpou.com.br").first()
        if not admin:
            admin = User(
                id="adm-1",
                name="Administrador Zarpou",
                email="admin@zarpou.com.br",
                password_hash=get_password_hash("admin123"),
                role="admin",
                allowed_screens=json.dumps(list(ALL_ADMIN_SCREENS)),
                is_active=True,
            )
            db.add(admin)

        juliana = db.query(User).filter(User.email == "juliana.costa@zarpou.com.br").first()
        if not juliana:
            juliana = User(
                id="adm-2",
                name="Juliana Costa",
                email="juliana.costa@zarpou.com.br",
                password_hash=get_password_hash("admin123"),
                role="personalizado",
                allowed_screens=json.dumps(["dashboard", "hero", "promocoes", "hospedagens", "passagens", "destinos", "reservas"]),
                is_active=True,
            )
            db.add(juliana)

        db.commit()
    finally:
        db.close()

    yield

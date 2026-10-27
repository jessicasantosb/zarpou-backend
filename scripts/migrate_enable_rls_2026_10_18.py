"""
Migração de segurança: habilita Row Level Security (RLS) em todas as tabelas
do schema public do Supabase.

Contexto (auditoria 2026-10-17/18):
- O backend FastAPI conecta como o papel `postgres` (dono das tabelas), que
  IGNORA RLS por padrão — habilitar RLS NÃO afeta a aplicação.
- Tabelas criadas pelo app (ex.: coupons, revoked_tokens) nascem sem RLS e,
  pelo default privileges do Supabase, ficam com grants para os papéis
  `anon`/`authenticated` usados pela Data API (PostgREST). Com a anon key
  (chave publicável, presente no frontend), qualquer pessoa podia LER e
  ESCRIVER essas tabelas direto, sem passar pelo backend.
- Com RLS habilitado e nenhuma policy definida, os papéis da Data API
  recebem ZERO acesso às tabelas públicas.

Este script também REVOKE dos papéis anon/authenticated (defesa em profundidade);
o backend continua funcionando normalmente (conecta como dono `postgres`).

Uso:
    venv\\Scripts\\python.exe -m scripts.migrate_enable_rls_2026_10_18

Idempotente: pode ser executado quantas vezes for preciso.
"""
from sqlalchemy import text

from app.core.database import Base, engine
import app.models  # noqa: F401  # Registra todos os modelos no Base.metadata

API_ROLES = ("anon", "authenticated")


def main() -> None:
    # Garante que as tabelas do modelo existam (ex.: customer_password_reset_tokens)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        tables = [
            row[0]
            for row in conn.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' ORDER BY tablename"
                )
            ).fetchall()
        ]

        roles_sql = ", ".join(f"'{r}'" for r in API_ROLES)
        existing_roles = {
            row[0]
            for row in conn.execute(
                text(f"SELECT rolname FROM pg_roles WHERE rolname IN ({roles_sql})")
            ).fetchall()
        }

        enabled, revoked = [], []
        for table in tables:
            # Habilita RLS (dono continua isento; Data API fica bloqueada sem policies)
            conn.execute(
                text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
            )
            enabled.append(table)

            # Defesa em profundidade: remove os grants diretos dos papéis da Data API
            roles = tuple(r for r in API_ROLES if r in existing_roles)
            if roles:
                # Literais para comparar com grantee (coluna de dados)...
                roles_literals = ", ".join(f"'{r}'" for r in roles)
                grants = conn.execute(
                    text(
                        "SELECT grantee FROM information_schema.role_table_grants "
                        "WHERE table_schema = 'public' AND table_name = :t "
                        f"AND grantee IN ({roles_literals}) LIMIT 1"
                    ),
                    {"t": table},
                ).fetchall()
                if grants:
                    # ...e identificadores no REVOKE (sintaxe de GRANT/REVOKE)
                    roles_identifiers = ", ".join(roles)
                    conn.execute(
                        text(
                            f"REVOKE ALL ON TABLE public.{table} FROM {roles_identifiers}"
                        )
                    )
                    revoked.append(table)

    print(f"RLS habilitado em {len(enabled)} tabelas: {', '.join(enabled)}")
    if revoked:
        print(f"Grants revogados de anon/authenticated em {len(revoked)} tabelas: {', '.join(revoked)}")
    print("Concluído. O backend (papel postgres/dono) segue funcionando normalmente.")


if __name__ == "__main__":
    main()

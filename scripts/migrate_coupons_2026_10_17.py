"""
Migração: criação da tabela de Cupons de Desconto (Zarpou).
Data: 2026-10-17

Cria a tabela 'coupons' (e seus índices) caso ela ainda não exista.
Compatível com SQLite e PostgreSQL.

Uso:
    venv\\Scripts\\python.exe -m scripts.migrate_coupons_2026_10_17

Observação: o Superadministrador ('admin') acessa a tela 'cupons' automaticamente.
Para os demais perfis (gestor, atendente, personalizado), inclua "cupons" na lista
allowed_screens do usuário pelo painel (/admin/administradores).
"""
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateIndex, CreateTable
from app.core.database import engine, Base
import app.models  # noqa: F401  # Registra todos os modelos no Base.metadata


def migrate():
    inspector = inspect(engine)
    if "coupons" in inspector.get_table_names():
        print("Tabela 'coupons' já existe. Nada a fazer.")
        return

    table = Base.metadata.tables["coupons"]
    statements = [str(CreateTable(table).compile(dialect=engine.dialect))]
    statements.extend(
        str(CreateIndex(index).compile(dialect=engine.dialect))
        for index in table.indexes
    )

    print("Criando tabela 'coupons'...")
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    print("Migração executada com sucesso no banco de dados!")
    print("Tabela 'coupons' criada com as colunas: id, code, description, discount_type, "
          "discount_value, min_order_amount, max_uses, used_count, per_customer_limit, "
          "valid_from, valid_to, active, created_by, created_at, updated_at.")


if __name__ == "__main__":
    migrate()

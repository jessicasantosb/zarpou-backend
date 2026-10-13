from sqlalchemy import text
from app.core.database import engine

def migrate():
    with engine.connect() as conn:
        print("Adicionando coluna allowed_screens se não existir...")
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_screens TEXT DEFAULT '[]';"))
        
        all_screens = '["dashboard","hero","promocoes","hospedagens","passagens","destinos","reservas","usuarios","administradores","configuracoes"]'
        conn.execute(text(f"""
            UPDATE users 
            SET allowed_screens = '{all_screens}'
            WHERE role = 'admin' AND (allowed_screens IS NULL OR allowed_screens = '[]' OR allowed_screens = '');
        """))
        conn.commit()
        print("Migração executada com sucesso no banco de dados!")

if __name__ == "__main__":
    migrate()

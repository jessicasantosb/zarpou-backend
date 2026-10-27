from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON
from app.core.database import Base


class ImportJob(Base):
    """
    Job de importação em massa (CSV/Excel) de catálogo.

    O arquivo é enviado pelo painel admin, persistido em disco e processado em
    background (Celery). Esta tabela guarda o ciclo de vida (pending ->
    processing -> completed | failed) e o relatório final de carga: quantas
    linhas foram importadas com sucesso e quais falharam (com o motivo).
    """
    __tablename__ = "import_jobs"

    id = Column(String(36), primary_key=True)  # uuid4
    resource = Column(String(30), nullable=False, index=True)  # hotels | destinations | flights | promotions | coupons
    mode = Column(String(10), nullable=False, default="upsert")  # 'upsert'
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending | processing | completed | failed
    original_filename = Column(String(255), nullable=True)
    stored_path = Column(String(500), nullable=True)
    total_rows = Column(Integer, nullable=False, default=0)
    processed_rows = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    report = Column(JSON, nullable=True)  # {"errors": [{"row": N, "code": "...", "error": "..."}]}
    message = Column(Text, nullable=True)  # motivo de falha de infra/estrutura do job
    created_by = Column(String(36), nullable=True)  # id do admin que enviou
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

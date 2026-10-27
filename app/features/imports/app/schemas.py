from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ImportRowError(BaseModel):
    row: int
    code: Optional[str] = None  # código da linha quando identificável (ex.: id/cupom)
    error: str


class ImportJobReport(BaseModel):
    errors: List[ImportRowError] = Field(default_factory=list)
    errors_truncated: bool = False  # relatório limitado a 500 erros detalhados


class ImportJobResponse(BaseModel):
    id: str
    resource: str
    mode: str
    status: str  # pending | processing | completed | failed
    original_filename: Optional[str] = None
    total_rows: int = 0
    processed_rows: int = 0
    success_count: int = 0
    error_count: int = 0
    message: Optional[str] = None
    report: Optional[Dict] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportJobCreated(BaseModel):
    """Resposta do upload: o job já foi aceito e será processado em background."""
    job: ImportJobResponse
    detail: str = (
        "Arquivo recebido. O processamento roda em segundo plano — "
        "acompanhe o progresso e o relatório de carga pela tela de importação."
    )

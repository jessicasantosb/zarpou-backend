"""
Serviço de importação em massa de catálogo (CSV/Excel → banco).

Fluxo:
1. Upload no painel: arquivo validado (tamanho/formato), salvo em disco e um
   ImportJob é criado com status 'pending'.
2. O job é despachado para a fila (Celery/Redis) — a requição HTTP retorna
   imediatamente (sem risco de 504 em arquivos grandes).
3. O worker processa linha a linha: coerção de tipos, campos obrigatórios,
   duplicados no arquivo e upsert por código; falhas de linha não derrubam a
   carga — são anotadas no relatório.
4. Ao final o job fica 'completed' com o relatório de carga (sucessos +
   falhas com o motivo linha a linha).
"""
import os
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.features.imports.app.importers import ImporterSpec, RowError, get_importer, hydrate_row
from app.features.imports.app.parsers import (
    ParseError,
    build_template_csv,
    build_template_xlsx,
    parse_import_file,
)
from app.features.imports.infra.models import ImportJob

UPLOAD_DIR = os.path.join("uploads", "imports")
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 50_000
MAX_REPORTED_ERRORS = 500
PROGRESS_BATCH = 50


class ImportError_(Exception):
    """Falha de estrutura do job (arquivo, colunas, fila) — não de linha."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_import_job(
    db: Session,
    resource: str,
    filename: str,
    content: bytes,
    mode: str,
    admin_id: Optional[str],
) -> ImportJob:
    """Valida o upload, persiste o arquivo e despacha o job para a fila."""
    spec = get_importer(resource)
    if spec is None:
        raise ImportError_(f"Recurso de importação desconhecido: '{resource}'.")

    lowered = (filename or "").lower()
    if not lowered.endswith((".csv", ".xlsx")):
        raise ImportError_("Formato não suportado. Envie um arquivo .csv ou .xlsx.")
    if len(content) > MAX_FILE_BYTES:
        raise ImportError_(f"Arquivo muito grande (máximo {MAX_FILE_BYTES // (1024 * 1024)} MB).")

    job = ImportJob(
        id=str(uuid.uuid4()),
        resource=resource,
        mode=mode or "upsert",
        status="pending",
        original_filename=filename,
        created_by=admin_id,
    )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extension = ".xlsx" if lowered.endswith(".xlsx") else ".csv"
    stored_path = os.path.join(UPLOAD_DIR, f"{job.id}{extension}")
    with open(stored_path, "wb") as handle:
        handle.write(content)
    job.stored_path = stored_path

    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        dispatch_import_job(job.id)
    except Exception:
        # Fila indisponível (Redis fora do ar): marca o job e sinaliza claramente.
        job.status = "failed"
        job.message = (
            "Fila de processamento indisponível (Redis/Celery). "
            "Verifique se o worker está ativo: celery -A app.core.celery_app.celery_app worker"
        )
        job.finished_at = _utcnow()
        db.commit()
        raise
    return job


def dispatch_import_job(job_id: str) -> None:
    """
    Enfileira o processamento. Isolado num função para os testes substituírem
    pelo processamento síncrono (sem Redis).
    """
    from app.features.imports.app.tasks import process_import_job_task

    process_import_job_task.delay(job_id)


def _finalize_failed(db: Session, job: ImportJob, message: str) -> None:
    job.status = "failed"
    job.message = message
    job.finished_at = _utcnow()
    db.commit()


def process_import_job(job_id: str) -> None:
    """Processa um job de importação (executa no worker Celery, com sessão própria)."""
    db = SessionLocal()
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job or job.status != "pending":
            return  # job inexistente ou já processado (idempotência)

        job.status = "processing"
        job.started_at = _utcnow()
        db.commit()

        spec = get_importer(job.resource)
        if spec is None:
            _finalize_failed(db, job, f"Recurso desconhecido: '{job.resource}'.")
            return

        try:
            with open(job.stored_path, "rb") as handle:
                file_bytes = handle.read()
            headers, rows = parse_import_file(job.original_filename or "", file_bytes)
        except (ParseError, OSError) as exc:
            _finalize_failed(db, job, f"Falha ao ler o arquivo: {exc}")
            return

        header_set = set(headers)
        # O cabeçalho precisa apenas da coluna-chave; campos obrigatórios só são
        # exigidos na criação de registros novos (permite updates parciais, ex.: só preços).
        if spec.key_field not in header_set:
            _finalize_failed(
                db,
                job,
                f"Coluna obrigatória ausente no cabeçalho: {spec.key_field}. "
                f"Baixe o template atualizado para conferir o formato.",
            )
            return

        if len(rows) > MAX_ROWS:
            _finalize_failed(db, job, f"Planilha com {len(rows)} linhas (máximo {MAX_ROWS}).")
            return

        job.total_rows = len(rows)
        db.commit()

        success_count = 0
        errors: List[Dict] = []
        error_count = 0
        seen_keys: Dict[object, int] = {}

        for row_number, row in rows:
            try:
                _import_row(db, spec, header_set, row, seen_keys, row_number)
                success_count += 1
            except RowError as exc:
                error_count += 1
                if len(errors) < MAX_REPORTED_ERRORS:
                    errors.append({
                        "row": row_number,
                        "code": _row_code(spec, row),
                        "error": str(exc),
                    })
            except Exception as exc:  # erro inesperado de banco não derruba a carga
                db.rollback()
                error_count += 1
                if len(errors) < MAX_REPORTED_ERRORS:
                    errors.append({
                        "row": row_number,
                        "code": _row_code(spec, row),
                        "error": f"Erro interno ao gravar: {exc}",
                    })

            processed = success_count + error_count
            if processed % PROGRESS_BATCH == 0:
                job.processed_rows = processed
                job.success_count = success_count
                job.error_count = error_count
                db.commit()

        job.processed_rows = success_count + error_count
        job.success_count = success_count
        job.error_count = error_count
        job.report = {"errors": errors, "errors_truncated": error_count > len(errors)}
        job.status = "completed"
        job.finished_at = _utcnow()
        db.commit()
    except Exception as exc:  # pragma: no cover - defesa de worker
        db.rollback()
        if failed_job := db.query(ImportJob).filter(ImportJob.id == job_id).first():
            _finalize_failed(db, failed_job, f"Falha inesperada no processamento: {exc}")
        traceback.print_exc()
    finally:
        db.close()


def _row_code(spec: ImporterSpec, row: Dict[str, str]) -> Optional[str]:
    value = row.get(spec.key_field)
    return str(value).strip() if value and str(value).strip() else None


def _import_row(
    db: Session,
    spec: ImporterSpec,
    header_set: set,
    row: Dict[str, str],
    seen_keys: Dict[object, int],
    row_number: int,
) -> None:
    """Valida e faz upsert de uma linha. Lança RowError para erros de dados."""
    data = hydrate_row(spec, header_set, row)

    key = data.get(spec.key_field)
    if key is None:
        raise RowError(f"campo obrigatório '{spec.key_field}' vazio")

    # Código duplicado dentro da própria planilha
    if key in seen_keys:
        raise RowError(f"código '{key}' duplicado na planilha (já usado na linha {seen_keys[key]})")
    seen_keys[key] = row_number

    key_column = getattr(spec.model, spec.key_field)
    existing = db.query(spec.model).filter(key_column == key).first()

    if existing is None:
        # Campos obrigatórios só são exigidos na criação (updates parciais são permitidos)
        missing = [col.name for col in spec.columns if col.required and col.name not in data]
        if missing:
            raise RowError(
                f"campo(s) obrigatório(s) ausente(s) para criar o registro: {', '.join(missing)}"
            )

    try:
        with db.begin_nested():
            if existing:
                for field_name, value in data.items():
                    setattr(existing, field_name, value)
            else:
                kwargs = dict(data)
                if spec.key_field != "id" and "id" not in kwargs and spec.make_id:
                    kwargs["id"] = spec.make_id(kwargs)
                db.add(spec.model(**kwargs))
    except Exception as exc:
        db.rollback()
        raise RowError(f"erro ao gravar no banco: {exc}") from exc


def list_jobs(db: Session, resource: str, limit: int = 20) -> List[ImportJob]:
    return (
        db.query(ImportJob)
        .filter(ImportJob.resource == resource)
        .order_by(ImportJob.created_at.desc())
        .limit(limit)
        .all()
    )


def get_job(db: Session, job_id: str) -> Optional[ImportJob]:
    return db.query(ImportJob).filter(ImportJob.id == job_id).first()


def recover_stale_jobs(db: Session, older_than_minutes: int = 60) -> int:
    """
    Chamado no startup: jobs 'pending'/'processing' antigos (servidor ou worker
    reiniciou no meio da carga) viram 'failed' para o painel não mostrar
    progresso eterno.
    """
    cutoff = _utcnow() - timedelta(minutes=older_than_minutes)
    stale = (
        db.query(ImportJob)
        .filter(ImportJob.status.in_(["pending", "processing"]))
        .filter(ImportJob.created_at < cutoff)
        .all()
    )
    for job in stale:
        job.status = "failed"
        job.message = "Processamento interrompido (servidor reiniciado). Envie o arquivo novamente."
        job.finished_at = _utcnow()
    db.commit()
    return len(stale)


def build_template(resource: str, fmt: str = "csv") -> Tuple[str, bytes, str]:
    """Retorna (nome_do_arquivo, bytes, content_type) do template do recurso."""
    spec = get_importer(resource)
    if spec is None:
        raise ImportError_(f"Recurso de importação desconhecido: '{resource}'.")
    if fmt == "xlsx":
        return f"template-{resource}.xlsx", build_template_xlsx(spec.columns), (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    return f"template-{resource}.csv", build_template_csv(spec.columns), "text/csv; charset=utf-8"

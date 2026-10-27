"""Tasks Celery do Zarpou Backend (executadas pelo worker: celery -A app.core.celery_app.celery_app worker)."""
from app.core.celery_app import celery_app


@celery_app.task(name="imports.process_job", bind=True)
def process_import_job_task(self, job_id: str) -> None:
    """Processa um ImportJob (leitura do arquivo + upsert linha a linha + relatório)."""
    from app.features.imports.app.services import process_import_job

    process_import_job(job_id)

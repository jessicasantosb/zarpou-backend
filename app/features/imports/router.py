from typing import Any, List
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_db
from app.features.users.infra.models import User
from app.features.imports.app.importers import IMPORTERS, get_importer
from app.features.imports.app.schemas import ImportJobCreated, ImportJobResponse
from app.features.imports.app.services import (
    ImportError_,
    build_template,
    create_import_job,
    get_job,
    list_jobs,
)

router = APIRouter()


def _get_spec_or_404(resource: str):
    spec = get_importer(resource)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurso de importação desconhecido: '{resource}'.",
        )
    return spec


def _check_resource_permission(admin: User, resource: str) -> None:
    """
    A importação herda a permissão da tela de destino: importar hotéis exige a
    tela 'hospedagens', cupons exige 'cupons', etc. Administrador Geral tem acesso
    irrestrito (mesma regra do require_screen).
    """
    spec = _get_spec_or_404(resource)
    if admin.role == "admin":
        return
    if spec.screen not in (admin.allowedScreens or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado: seu perfil não possui permissão para o módulo '{spec.screen}'.",
        )


@router.get("/resources")
def list_import_resources() -> Any:
    """Lista os recursos de catálogo disponíveis para importação (com colunas do template)."""
    return [
        {
            "resource": spec.resource,
            "label": spec.label,
            "screen": spec.screen,
            "keyField": spec.key_field,
            "requiredColumns": spec.required_columns,
            "columns": [
                {
                    "name": col.name,
                    "required": col.required,
                    "kind": col.kind,
                    "example": col.example,
                    "description": col.description,
                }
                for col in spec.columns
            ],
        }
        for spec in IMPORTERS.values()
    ]


@router.get("/{resource}/template")
def download_template(
    resource: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    admin: User = Depends(get_current_admin_user),
) -> Any:
    """Baixa o template (CSV ou XLSX) com as colunas corretas do recurso (Requer Admin)."""
    _check_resource_permission(admin, resource)
    try:
        filename, content, content_type = build_template(resource, format)
    except ImportError_ as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{resource}", response_model=ImportJobCreated, status_code=status.HTTP_202_ACCEPTED)
async def upload_import_file(
    resource: str,
    file: UploadFile = File(...),
    mode: str = Form("upsert"),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """
    Envia planilha (CSV/XLSX) para importação em massa (Requer Admin).
    O processamento roda em background (Celery) — acompanhe via GET /imports/{resource}/jobs.
    """
    _check_resource_permission(admin, resource)
    content = await file.read()
    try:
        job = create_import_job(
            db=db,
            resource=resource,
            filename=file.filename or "",
            content=content,
            mode=mode,
            admin_id=admin.id,
        )
    except ImportError_ as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ImportJobCreated(job=ImportJobResponse.model_validate(job))


@router.get("/{resource}/jobs", response_model=List[ImportJobResponse])
def list_resource_jobs(
    resource: str,
    limit: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Histórico de importações do recurso, com progresso e relatório (Requer Admin)."""
    _check_resource_permission(admin, resource)
    return list_jobs(db, resource, limit)


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
def get_import_job(
    job_id: str,
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Status e relatório de carga de um job de importação (Requer Admin)."""
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job de importação não encontrado.",
        )
    _check_resource_permission(admin, job.resource)
    return job

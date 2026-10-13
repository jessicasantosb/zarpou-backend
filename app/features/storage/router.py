from fastapi import APIRouter, File, UploadFile, Query, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.features.storage.app.schemas import UploadResponse
from app.features.storage.app.services import StorageService

router = APIRouter()


@router.post("/upload", response_model=UploadResponse, summary="Upload de imagem")
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Query("banners", description="Pasta de destino (ex: banners, hero, promocoes, destinos)"),
    db: Session = Depends(get_db),
):
    """
    Realiza o upload de imagens para AWS S3 (ou Supabase Storage se configurado).
    Gera link público direto na CDN do bucket. Caso as credenciais em nuvem
    ainda não estejam configuradas, salva localmente e serve via link público.
    """
    content = await file.read()
    service = StorageService(db)
    return await service.upload_file(
        content=content,
        original_filename=file.filename or "image",
        content_type=file.content_type or "application/octet-stream",
        folder=folder,
    )

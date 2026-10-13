import os
import re
import uuid
import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.features.agency.app.services import AgencyService
from app.features.storage.domain.entities import UploadResultEntity
from app.features.storage.infra.storage_providers import (
    S3StorageProvider,
    SupabaseStorageProvider,
    LocalStorageProvider,
)
from app.features.storage.app.schemas import UploadResponse

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def sanitize_name(name: str) -> str:
    clean = re.sub(r"[^\w\.-]", "_", name)
    return clean.lower()


class StorageService:
    def __init__(self, db: Session):
        self.db = db

    def validate_file(self, content: bytes, content_type: str) -> str:
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato de arquivo não suportado. Envie apenas imagens JPG, PNG, WebP, GIF ou SVG.",
            )
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo ultrapassa o limite máximo permitido de 10MB.",
            )
        return ALLOWED_MIME_TYPES[content_type]

    async def upload_file(
        self,
        content: bytes,
        original_filename: str,
        content_type: str,
        folder: str = "banners",
    ) -> UploadResponse:
        ext = self.validate_file(content, content_type)
        stem = sanitize_name(os.path.splitext(original_filename or "image")[0])
        unique_name = f"{uuid.uuid4().hex[:10]}_{stem}{ext}"
        clean_folder = sanitize_name(folder).strip("/") or "banners"

        # 1. Tentativa via AWS S3 / Cloudflare R2 configurado no Banco de Dados (Painel da Agência)
        try:
            agency_settings = AgencyService(self.db).get_settings()
            storage_cfg = agency_settings.storageBucket
            if (
                storage_cfg.enabled
                and storage_cfg.provider in ["aws_s3", "cloudflare_r2"]
                and storage_cfg.bucketName
                and storage_cfg.accessKeyId
                and storage_cfg.secretAccessKey
            ):
                provider = S3StorageProvider(
                    bucket_name=storage_cfg.bucketName,
                    access_key_id=storage_cfg.accessKeyId,
                    secret_access_key=storage_cfg.secretAccessKey,
                    region=storage_cfg.region or "sa-east-1",
                    endpoint_url=storage_cfg.endpointUrl or None,
                    public_url_prefix=storage_cfg.publicUrlPrefix or None,
                    provider_name=storage_cfg.provider,
                )
                res = await provider.upload(content, unique_name, content_type, clean_folder)
                return self._to_response(res)
        except Exception as exc:
            logger.warning("[Storage] Falha no upload AWS S3 via configurações da agência: %s", exc)

        # 2. Tentativa via AWS S3 configurado nas variáveis de ambiente (.env)
        if (
            settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
            and settings.AWS_S3_BUCKET
        ):
            try:
                provider = S3StorageProvider(
                    bucket_name=settings.AWS_S3_BUCKET,
                    access_key_id=settings.AWS_ACCESS_KEY_ID,
                    secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region=settings.AWS_REGION or "sa-east-1",
                    endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
                    public_url_prefix=settings.AWS_S3_PUBLIC_URL_PREFIX or None,
                    provider_name="aws_s3",
                )
                res = await provider.upload(content, unique_name, content_type, clean_folder)
                return self._to_response(res)
            except Exception as exc:
                logger.warning("[Storage] Falha no upload AWS S3 via .env: %s", exc)

        # 3. Tentativa via Supabase Storage REST API
        supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
        if supabase_key and settings.SUPABASE_URL and settings.SUPABASE_BUCKET:
            try:
                provider = SupabaseStorageProvider(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=supabase_key,
                    bucket_name=settings.SUPABASE_BUCKET,
                )
                res = await provider.upload(content, unique_name, content_type, clean_folder)
                return self._to_response(res)
            except Exception as exc:
                logger.warning("[Storage] Falha no upload Supabase Storage: %s", exc)

        # 4. Fallback Local Gracioso
        local_provider = LocalStorageProvider()
        res = await local_provider.upload(content, unique_name, content_type, clean_folder)
        return self._to_response(res)

    def _to_response(self, entity: UploadResultEntity) -> UploadResponse:
        return UploadResponse(
            success=entity.success,
            url=entity.url,
            provider=entity.provider,
            filename=entity.filename,
            folder=entity.folder,
            size=entity.size,
            contentType=entity.content_type,
        )

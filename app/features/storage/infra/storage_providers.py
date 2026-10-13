import os
import asyncio
import httpx
from typing import Optional
from app.features.storage.domain.entities import UploadResultEntity
from app.features.storage.domain.repositories import IStorageProvider


class S3StorageProvider:
    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "sa-east-1",
        endpoint_url: Optional[str] = None,
        public_url_prefix: Optional[str] = None,
        provider_name: str = "aws_s3",
    ):
        self.bucket_name = bucket_name
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.region = region or "sa-east-1"
        self.endpoint_url = endpoint_url
        self.public_url_prefix = public_url_prefix
        self.provider_name = provider_name

    async def upload(self, content: bytes, filename: str, content_type: str, folder: str) -> UploadResultEntity:
        storage_path = f"{folder}/{filename}"

        def _sync_put():
            import boto3
            from botocore.config import Config

            boto_kwargs = {
                "service_name": "s3",
                "aws_access_key_id": self.access_key_id,
                "aws_secret_access_key": self.secret_access_key,
                "region_name": self.region,
                "config": Config(signature_version="s3v4"),
            }
            if self.endpoint_url:
                boto_kwargs["endpoint_url"] = self.endpoint_url

            s3_client = boto3.client(**boto_kwargs)
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=storage_path,
                Body=content,
                ContentType=content_type,
            )

        await asyncio.to_thread(_sync_put)

        if self.public_url_prefix:
            public_url = f"{self.public_url_prefix.rstrip('/')}/{storage_path}"
        elif self.endpoint_url:
            public_url = f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{storage_path}"
        else:
            public_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_path}"

        return UploadResultEntity(
            success=True,
            url=public_url,
            provider=self.provider_name,
            filename=filename,
            folder=folder,
            size=len(content),
            content_type=content_type,
        )


class SupabaseStorageProvider:
    def __init__(self, supabase_url: str, supabase_key: str, bucket_name: str = "zarpou-media"):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.bucket_name = bucket_name

    async def upload(self, content: bytes, filename: str, content_type: str, folder: str) -> UploadResultEntity:
        storage_path = f"{folder}/{filename}"
        upload_url = f"{self.supabase_url.rstrip('/')}/storage/v1/object/{self.bucket_name}/{storage_path}"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(upload_url, headers=headers, content=content)
            if res.status_code not in (200, 201):
                raise RuntimeError(f"Supabase Storage returned {res.status_code}: {res.text}")

        public_url = f"{self.supabase_url.rstrip('/')}/storage/v1/object/public/{self.bucket_name}/{storage_path}"
        return UploadResultEntity(
            success=True,
            url=public_url,
            provider="supabase",
            filename=filename,
            folder=folder,
            size=len(content),
            content_type=content_type,
        )


class LocalStorageProvider:
    def __init__(self, base_dir: str = "uploads", base_url: str = "http://localhost:8000/uploads"):
        self.base_dir = base_dir
        self.base_url = base_url

    async def upload(self, content: bytes, filename: str, content_type: str, folder: str) -> UploadResultEntity:
        clean_folder = folder.strip("/")
        target_dir = os.path.join(self.base_dir, clean_folder)
        os.makedirs(target_dir, exist_ok=True)
        local_path = os.path.join(target_dir, filename)

        def _sync_write():
            with open(local_path, "wb") as f:
                f.write(content)

        await asyncio.to_thread(_sync_write)

        public_url = f"{self.base_url.rstrip('/')}/{clean_folder}/{filename}"
        return UploadResultEntity(
            success=True,
            url=public_url,
            provider="local",
            filename=filename,
            folder=clean_folder,
            size=len(content),
            content_type=content_type,
        )

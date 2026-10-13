from typing import Protocol
from app.features.storage.domain.entities import UploadResultEntity


class IStorageProvider(Protocol):
    async def upload(self, content: bytes, filename: str, content_type: str, folder: str) -> UploadResultEntity:
        ...

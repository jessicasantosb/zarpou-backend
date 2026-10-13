from dataclasses import dataclass
from typing import Optional


@dataclass
class UploadResultEntity:
    success: bool
    url: str
    provider: str  # 'aws_s3', 'cloudflare_r2', 'supabase', 'local'
    filename: str
    folder: str
    size: int
    content_type: str

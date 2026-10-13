from pydantic import BaseModel, Field, AliasChoices, ConfigDict


class UploadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = True
    url: str
    provider: str  # 'aws_s3', 'cloudflare_r2', 'supabase', 'local'
    filename: str
    folder: str
    size: int
    contentType: str = Field(..., validation_alias=AliasChoices("contentType", "content_type"))

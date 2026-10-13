from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ChatMessage(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str


class SuggestedAction(BaseModel):
    label: str
    url: str


class ChatRequestConfig(BaseModel):
    provider: Optional[str] = "openai"
    apiKey: Optional[str] = None
    model: Optional[str] = "gpt-4o-mini"
    systemPrompt: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    sessionId: Optional[str] = "default-session"
    config: Optional[ChatRequestConfig] = None


class ChatResponse(BaseModel):
    reply: str
    suggestedActions: Optional[List[SuggestedAction]] = []


class ChatLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sessionId: str
    role: str
    content: str
    createdAt: datetime

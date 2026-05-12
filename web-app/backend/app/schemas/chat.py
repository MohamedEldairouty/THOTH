from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    language: str = "en"
    exhibit_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    language: str
    audio_base64: str | None = None  # base64 MP3, present when TTS is requested


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}

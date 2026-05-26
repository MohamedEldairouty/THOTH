from fastapi import APIRouter, Depends, File, Form, UploadFile, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.voice_service import text_to_speech_base64

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Text chat — calls Gemini, returns text reply + TTS audio."""
    return ChatService.handle_message(db, payload, with_tts=True)


@router.post("/voice", response_model=ChatResponse)
async def chat_voice(
    audio: UploadFile = File(...),
    session_id: int | None = Form(None),
    exhibit_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """Voice chat — receives audio, runs Whisper STT → Gemini → edge-tts, returns text + audio."""
    audio_bytes = await audio.read()
    return ChatService.handle_voice_message(db, audio_bytes, session_id, exhibit_id)


# ── Standalone TTS — used for the auto-greeting and any UI strings ─────


class TTSRequest(BaseModel):
    text: str
    language: str = "en"


class TTSResponse(BaseModel):
    audio_base64: str | None
    language: str


@router.post("/tts", response_model=TTSResponse)
def chat_tts(payload: TTSRequest):
    """Convert arbitrary text to TTS audio in the given language.
    Returns base64 MP3 — used by the frontend for the chat auto-greeting
    so it doesn't have to round-trip through the LLM."""
    lang = (payload.language or "en").lower()
    if lang not in ("en", "ar", "fr"):
        lang = "en"
    try:
        b64 = text_to_speech_base64(payload.text, lang)
    except Exception as e:
        print(f"[chat/tts] failed: {e}")
        b64 = None
    return TTSResponse(audio_base64=b64, language=lang)

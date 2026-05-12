from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Text chat — calls Gemini, returns text reply (+ optional TTS)."""
    return ChatService.handle_message(db, payload, with_tts=False)


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

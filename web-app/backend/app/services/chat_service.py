from sqlalchemy.orm import Session

from app.models.chat import ChatSession, ChatMessage
from app.models.exhibit import Exhibit
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import ask_gemini
from app.services.voice_service import text_to_speech_base64


class ChatService:
    @staticmethod
    def handle_message(db: Session, payload: ChatRequest, with_tts: bool = False) -> ChatResponse:
        # Resolve or create session
        session = None
        if payload.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()

        if not session:
            session = ChatSession(
                language=payload.language,
                current_exhibit_id=payload.exhibit_id,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # Build exhibit context so Gemini knows what the visitor is looking at
        exhibit_context = None
        exhibit_id = payload.exhibit_id or session.current_exhibit_id
        if exhibit_id:
            exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
            if exhibit:
                exhibit_context = getattr(exhibit, f"title_{payload.language}", exhibit.title_en)

        # Persist user message
        db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
        db.commit()

        # Call real Gemini LLM
        reply = ask_gemini(payload.message, exhibit_context=exhibit_context)

        # Persist assistant response
        db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
        db.commit()

        # Optionally generate TTS audio
        audio_b64 = text_to_speech_base64(reply, payload.language) if with_tts else None

        return ChatResponse(
            reply=reply,
            session_id=session.id,
            language=payload.language,
            audio_base64=audio_b64,
        )

    @staticmethod
    def handle_voice_message(
        db: Session,
        audio_bytes: bytes,
        session_id: int | None,
        exhibit_id: int | None,
    ) -> ChatResponse:
        from app.services.voice_service import transcribe_audio

        # Transcribe audio → text + detected language
        text, language = transcribe_audio(audio_bytes)

        if not text:
            return ChatResponse(reply="", session_id=session_id or 0, language=language)

        payload = ChatRequest(
            message=text,
            session_id=session_id,
            language=language,
            exhibit_id=exhibit_id,
        )
        # Always return TTS audio for voice messages
        return ChatService.handle_message(db, payload, with_tts=True)

from sqlalchemy.orm import Session

from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    @staticmethod
    def handle_message(db: Session, payload: ChatRequest) -> ChatResponse:
        # Resolve or create session
        if payload.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
        else:
            session = None

        if not session:
            session = ChatSession(
                language=payload.language,
                current_exhibit_id=payload.exhibit_id,
            )
            db.add(session)
            db.commit()
            db.refresh(session)

        # Persist user message
        user_msg = ChatMessage(session_id=session.id, role="user", content=payload.message)
        db.add(user_msg)
        db.commit()

        # TODO: replace stub with real LLM service call
        reply = _stub_reply(payload.message, payload.language)

        # Persist assistant response
        assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=reply)
        db.add(assistant_msg)
        db.commit()

        return ChatResponse(reply=reply, session_id=session.id, language=payload.language)


def _stub_reply(message: str, lang: str) -> str:
    """Temporary placeholder until LLM service is wired in."""
    greetings = {
        "en": "Hello! I am THOTH, your museum guide. How can I help you explore the Grand Egyptian Museum?",
        "ar": "مرحباً! أنا تحوت، مرشدك في المتحف. كيف يمكنني مساعدتك في استكشاف المتحف المصري الكبير؟",
        "fr": "Bonjour ! Je suis THOTH, votre guide du musée. Comment puis-je vous aider à explorer le Grand Musée Égyptien ?",
    }
    return greetings.get(lang, greetings["en"])

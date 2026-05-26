import re

from sqlalchemy.orm import Session

from app.models.chat import ChatSession, ChatMessage
from app.models.exhibit import Exhibit
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import ask_gemini
from app.services.voice_service import text_to_speech_base64


# ── Language detection ───────────────────────────────────────────────────
# We support TTS for ar/en/fr. For any other language we still let Gemini
# reply (mirroring whatever the visitor used), but skip TTS so we don't try
# to speak Spanish with an Arabic voice.

SUPPORTED_TTS_LANGS = {"ar", "en", "fr"}

_ARABIC_RX = re.compile(r"[؀-ۿ]")
_FRENCH_CHARS_RX = re.compile(r"[éèêëàâçîïôûùüœÉÈÊËÀÂÇÎÏÔÛÙÜŒ]")
_FRENCH_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "du", "de",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
    "est", "suis", "es", "sont", "etes", "êtes",
    "et", "ou", "mais", "donc", "où", "ce", "cette", "ces",
    "bonjour", "merci", "oui", "non", "quoi", "quel", "quelle",
    "c'est", "n'est", "j'ai", "j'aime",
    "pourquoi", "comment", "quand", "qui",
}
_ENGLISH_STOPWORDS = {
    # 'was' is omitted on purpose — it also exists in German.
    "the", "an", "is", "are", "were", "be", "been",
    "i", "you", "he", "she", "it", "we", "they",
    "what", "where", "who", "how", "when", "why", "which",
    "can", "could", "would", "should", "do", "does", "did",
    "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "this", "that", "these", "those",
    "hi", "hello", "hey", "thanks", "please", "tell", "show", "me",
}


def detect_language(text: str) -> str:
    """Return 'ar' | 'en' | 'fr' | 'other'.

    Lightweight heuristic — fine for our 3-language use case. For anything
    else we return 'other' so the LLM still mirrors the visitor's language
    but we skip TTS.
    """
    if not text:
        return "en"
    if _ARABIC_RX.search(text):
        return "ar"
    if _FRENCH_CHARS_RX.search(text):
        return "fr"

    words = re.findall(r"[A-Za-z']+", text.lower())
    if not words:
        return "en"
    fr_hits = sum(1 for w in words if w in _FRENCH_STOPWORDS)
    en_hits = sum(1 for w in words if w in _ENGLISH_STOPWORDS)

    # French needs a clear signal (≥2 stopword hits) since some markers
    # like "que" / "le" overlap with Spanish/Portuguese.
    if fr_hits >= 2 and fr_hits > en_hits:
        return "fr"
    # English needs ≥2 stopword hits OR a single hit when it's clearly
    # a tiny English-style query (≤3 words like "tell me about").
    if en_hits >= 2 and en_hits >= fr_hits:
        return "en"
    if en_hits >= 1 and fr_hits == 0 and len(words) <= 3:
        return "en"

    # Latin script but no familiar markers — likely some other language
    # (Spanish, German, Italian, etc.). Let the LLM mirror it; we won't TTS.
    return "other"


# ── Apology fallback ─────────────────────────────────────────────────────

_APOLOGY = {
    "en": "Sorry — I had a brief issue answering that. Could you try once more?",
    "ar": "آسف — واجهت مشكلة قصيرة في الإجابة. هل يمكنك المحاولة مرة أخرى؟",
    "fr": "Désolé — j'ai eu un petit problème pour répondre. Pouvez-vous réessayer?",
}


def _fallback_apology(lang: str) -> str:
    return _APOLOGY.get(lang, _APOLOGY["en"])


# ── Service ──────────────────────────────────────────────────────────────

_HISTORY_LIMIT = 10  # last N user+assistant turns we send to the LLM


class ChatService:
    @staticmethod
    def handle_message(db: Session, payload: ChatRequest, with_tts: bool = False) -> ChatResponse:
        # 1) Resolve / create session
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

        # 2) Exhibit context
        exhibit_context = None
        exhibit_id = payload.exhibit_id or session.current_exhibit_id
        if exhibit_id:
            exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
            if exhibit:
                # Use the language of the CURRENT message so the title matches
                # what Gemini will reply in (best effort — falls back to EN).
                msg_lang = detect_language(payload.message)
                attr_lang = msg_lang if msg_lang in ("en", "ar", "fr") else "en"
                exhibit_context = getattr(exhibit, f"title_{attr_lang}", exhibit.title_en)

        # 3) Pull conversation history BEFORE persisting the new user turn,
        #    so the model sees prior turns as context, not the current one twice.
        history_rows = (
            db.query(ChatMessage)
              .filter(ChatMessage.session_id == session.id)
              .order_by(ChatMessage.id.desc())
              .limit(_HISTORY_LIMIT)
              .all()
        )
        history = [
            {"role": m.role, "content": m.content}
            for m in reversed(history_rows)
        ]

        # 4) Persist user message
        db.add(ChatMessage(session_id=session.id, role="user", content=payload.message))
        db.commit()

        # 5) Detect language of THIS message — this drives both the LLM hint
        #    and the TTS voice. Fall back to payload.language if heuristic
        #    came up empty.
        detected = detect_language(payload.message)
        if detected == "other":
            # Pass payload.language as a soft hint to the LLM only when our
            # heuristic is unsure; the LLM still mirrors the visitor's actual
            # language because the message itself is in the prompt.
            llm_hint = None
        else:
            llm_hint = detected

        # 6) Ask Gemini
        try:
            reply = ask_gemini(
                payload.message,
                exhibit_context=exhibit_context,
                history=history,
                detected_lang=llm_hint,
            )
        except Exception as e:
            print(f"[chat] LLM error (detected={detected}): {e}")
            reply = _fallback_apology(detected if detected != "other" else "en")

        # 7) Persist assistant reply
        db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
        # Keep session.language in sync with the latest detected language so
        # subsequent calls have a sensible default.
        if detected in ("en", "ar", "fr"):
            session.language = detected
        db.commit()

        # 8) TTS — only for supported languages. We re-detect from the REPLY
        #    so the voice matches what Gemini actually wrote (more robust
        #    than trusting `detected` if the LLM ignored our hint).
        audio_b64 = None
        reply_lang = detect_language(reply)
        if with_tts and reply_lang in SUPPORTED_TTS_LANGS:
            try:
                audio_b64 = text_to_speech_base64(reply, reply_lang)
            except Exception as e:
                print(f"[chat] TTS error in lang={reply_lang}: {e}")
        elif with_tts:
            print(f"[chat] skipping TTS — reply language '{reply_lang}' not in {SUPPORTED_TTS_LANGS}")

        return ChatResponse(
            reply=reply,
            session_id=session.id,
            language=reply_lang if reply_lang != "other" else (detected if detected != "other" else "en"),
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

        # Transcribe audio → text + Whisper's detected language
        text, whisper_lang = transcribe_audio(audio_bytes)

        if not text:
            return ChatResponse(reply="", session_id=session_id or 0, language=whisper_lang)

        # We trust Whisper's lang as the initial hint, but handle_message
        # will re-detect from the transcribed text anyway, so the two agree
        # for ar/en/fr and the LLM still mirrors any other language.
        payload = ChatRequest(
            message=text,
            session_id=session_id,
            language=whisper_lang,
            exhibit_id=exhibit_id,
        )
        return ChatService.handle_message(db, payload, with_tts=True)

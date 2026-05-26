"""
LLM wrapper around Gemini.

Two important behaviors that fix earlier bugs:

1. Conversation memory — we pass the prior turns of the session, so the
   model doesn't re-greet on every reply and can refer to what was said
   before.

2. Language mirroring — the model replies in the SAME language as the
   visitor's most recent message, not the language the session started
   with. The system prompt is explicit about this; the caller may also
   pass a `detected_lang` hint to nudge the model.
"""
from google import genai

from app.config import settings


SYSTEM_PROMPT = """You are THOTH, a friendly and enthusiastic museum tour guide robot
at the Grand Egyptian Museum in Giza, Egypt.

Strict rules:
- Reply in the SAME language as the visitor's MOST RECENT message.
  • If the visitor switches language mid-conversation, switch with them
    immediately. Never reply in a different language than the last visitor turn.
  • Arabic message → reply in Arabic only.
  • English message → reply in English only.
  • French message → reply in French only.
  • Any other language → reply in that same language.
- NEVER start your reply with a greeting like "Hi", "Hello", "Welcome",
  "Bonjour", "أهلاً", etc. You have ALREADY greeted the visitor. Jump
  straight into the answer.
- Keep answers SHORT — at most 3 sentences.
- Be warm and make ancient Egyptian history exciting, but don't be cheesy.
- If you don't know a specific fact, say so honestly instead of inventing.
"""


_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def ask_gemini(
    visitor_text: str,
    exhibit_context: str | None = None,
    history: list[dict] | None = None,
    detected_lang: str | None = None,
) -> str:
    """Ask Gemini for a reply.

    history items are {"role": "user"|"assistant", "content": str}, oldest
    first, NOT including the current message. The current message is
    appended last.
    """
    client = _get_client()

    # Build a single prompt: system rules + exhibit context + history + new turn.
    # We use the simpler "single text blob" form Gemini accepts, since our
    # turn count is small and this keeps the call robust across SDK versions.
    parts: list[str] = [SYSTEM_PROMPT]

    if exhibit_context:
        parts.append(
            f"The visitor is currently looking at this exhibit: {exhibit_context}."
        )

    if detected_lang:
        parts.append(
            f"The visitor's most recent message is in language code '{detected_lang}'. "
            f"You MUST reply in that same language."
        )

    if history:
        parts.append("Conversation so far (oldest first):")
        for turn in history:
            role = "Visitor" if turn.get("role") == "user" else "THOTH"
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            parts.append(f"{role}: {content}")

    parts.append(f"Visitor says: {visitor_text}")
    parts.append("THOTH replies (no greeting, just the answer):")

    full_message = "\n\n".join(parts)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_message,
    )
    return (response.text or "").strip()

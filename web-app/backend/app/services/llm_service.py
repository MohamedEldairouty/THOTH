from google import genai
from app.config import settings

SYSTEM_PROMPT = """You are THOTH, a friendly and enthusiastic museum tour guide robot
at the Grand Egyptian Museum in Giza, Egypt.

Your rules:
- Always reply in the SAME language the visitor used
- If they speak Arabic, reply in Arabic
- If they speak English, reply in English
- If they speak French, reply in French
- Keep answers SHORT — maximum 3 sentences
- Be warm, friendly, and make history exciting
- If you don't know something specific, say so honestly
"""

_client = None


def _get_client():
    global _client

    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")

        _client = genai.Client(api_key=settings.GEMINI_API_KEY)

    return _client


def ask_gemini(visitor_text: str, exhibit_context: str | None = None) -> str:
    try:
        client = _get_client()

        context = (
            f"\n\nThe visitor is currently looking at this exhibit: {exhibit_context}"
            if exhibit_context
            else ""
        )

        full_message = f"{SYSTEM_PROMPT}{context}\n\nVisitor says: {visitor_text}"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_message,
        )

        return response.text.strip()

    except Exception as e:
        return f"AI service is temporarily unavailable. Error: {str(e)}"
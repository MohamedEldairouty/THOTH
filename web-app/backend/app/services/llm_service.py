import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are THOTH, a friendly and enthusiastic museum tour guide robot
at the Grand Egyptian Museum in Giza, Egypt.

Your rules:
- Always reply in the SAME language the visitor used
- If they speak Arabic, reply in Arabic
- If they speak English, reply in English
- If they speak French, reply in French
- Keep answers SHORT — maximum 3 sentences, this is real-time conversation
- Be warm, friendly, and make history exciting
- You are talking to museum visitors of all ages including children
- If you don't know something specific, say so honestly
"""

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=api_key)
    return _client


def ask_gemini(visitor_text: str, exhibit_context: str | None = None) -> str:
    client = _get_client()
    context = f"\n\nThe visitor is currently looking at this exhibit: {exhibit_context}" if exhibit_context else ""
    full_message = f"{SYSTEM_PROMPT}{context}\n\nVisitor says: {visitor_text}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_message
    )
    return response.text.strip()

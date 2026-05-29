"""
LLM wrapper around Gemini.

Three important behaviors:

1. Conversation memory — we pass the prior turns of the session, so the
   model doesn't re-greet on every reply and can refer to what was said
   before.

2. Language mirroring — the model replies in the SAME language as the
   visitor's most recent message, not the language the session started
   with. The system prompt is explicit about this; the caller may also
   pass a `detected_lang` hint to nudge the model.

3. Adaptive tone via vision — when a fresh, high-confidence age/mood
   profile is available, `build_persona_hint()` translates it into a
   short instruction in the reply language (EN/AR/FR) and the prompt
   weaves it in. Low confidence or missing profile → no hint → today's
   default tone.
"""
import time
from typing import Optional, TYPE_CHECKING

from google import genai

from app.config import settings

if TYPE_CHECKING:
    # Avoid runtime import cycle: vision_service may import llm_service
    # in the future for diagnostics. TYPE_CHECKING-only is safe.
    from app.services.vision_service import VisionProfile


# Errors that are worth a quick automatic retry (Gemini free tier flakes
# under load — most 503s clear within a couple of seconds).
_TRANSIENT_ERR_SUBSTRINGS = (
    "503",
    "UNAVAILABLE",
    "overloaded",
    "RESOURCE_EXHAUSTED",
    "429",
    "deadline",
    "timeout",
)


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s.lower() in msg for s in _TRANSIENT_ERR_SUBSTRINGS)


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
- When referring to yourself in Arabic, ALWAYS write your name as
  "تحوت" (the proper Arabic name of the Egyptian god of wisdom — Thoth).
  NEVER write "توت" — that is a different word (mulberry) and the TTS
  voice will mispronounce it as "Tut".
"""


# ─────────────────────────────────────────────────────────────────────────
# Adaptive tone (driven by vision_service)
# ─────────────────────────────────────────────────────────────────────────

# Multilingual tone snippets. Keep each one SHORT — Gemini follows the
# spirit, not the letter. Longer snippets just push the model to parrot.
_AGE_TONE = {
    "child": {
        "en": "The visitor is a child (around 8). Use simple, playful words, "
              "short sentences, and add a touch of wonder.",
        "ar": "الزائر طفل صغير. استخدم كلمات بسيطة ومرحة وجمل قصيرة وأضف لمسة من الدهشة.",
        "fr": "Le visiteur est un enfant. Utilise des mots simples, des phrases "
              "courtes et un ton émerveillé.",
    },
    "teen": {
        "en": "The visitor is a teenager. Be energetic and direct, less formal, "
              "punchier sentences.",
        "ar": "الزائر مراهق. كن حيويًا ومباشرًا، أقل رسمية، وجملك قصيرة وحماسية.",
        "fr": "Le visiteur est un adolescent. Sois énergique, direct, "
              "phrases courtes et un peu décontracté.",
    },
    "adult": {
        # No special instruction — default tone IS the adult tone. Leaving
        # this empty keeps the prompt clean when the bucket is "adult".
        "en": "",
        "ar": "",
        "fr": "",
    },
    "senior": {
        "en": "The visitor is an older adult. Speak with calm pacing and a "
              "respectful tone; avoid slang.",
        "ar": "الزائر شخص مسنّ. تحدث بإيقاع هادئ ولهجة محترمة، وتجنب العامية.",
        "fr": "Le visiteur est une personne âgée. Parle posément, sur un ton "
              "respectueux, sans argot.",
    },
}

_MOOD_TONE = {
    "happy": {
        "en": "The visitor seems happy — match their energy warmly.",
        "ar": "يبدو الزائر سعيدًا — جاريه بدفء وحماس.",
        "fr": "Le visiteur a l'air heureux — accompagne son énergie chaleureusement.",
    },
    "surprise": {
        "en": "The visitor seems surprised or curious — feed that curiosity.",
        "ar": "يبدو الزائر متفاجئًا أو فضوليًا — أشبع فضوله.",
        "fr": "Le visiteur a l'air surpris ou curieux — nourris cette curiosité.",
    },
    "sad": {
        "en": "The visitor seems a little down. Be gentle, no exclamation marks. "
              "You may briefly ask if everything is okay before continuing.",
        "ar": "يبدو الزائر متضايقًا قليلاً. كن لطيفًا، لا تستخدم علامات تعجب. "
              "يمكنك أن تسأل باختصار إن كان كل شيء على ما يرام قبل المتابعة.",
        "fr": "Le visiteur semble un peu triste. Sois doux, pas de points "
              "d'exclamation. Tu peux brièvement demander si tout va bien avant de continuer.",
    },
    "fear": {
        "en": "The visitor looks uneasy. Speak calmly and reassuringly, "
              "shorter sentences.",
        "ar": "يبدو الزائر قلقًا. تحدث بهدوء وطمأنينة وبجمل قصيرة.",
        "fr": "Le visiteur semble mal à l'aise. Parle calmement, en phrases "
              "courtes, sur un ton rassurant.",
    },
    "angry": {
        "en": "The visitor seems frustrated. Stay calm, be concise and helpful, "
              "no jokes.",
        "ar": "يبدو الزائر منزعجًا. ابقَ هادئًا، وكن مختصرًا ومفيدًا، بدون مزاح.",
        "fr": "Le visiteur semble agacé. Reste calme, sois concis et utile, "
              "pas de plaisanteries.",
    },
    "disgust": {
        # Disgust on FER2013 is the noisiest class — fold to neutral guidance.
        "en": "",
        "ar": "",
        "fr": "",
    },
    "neutral": {
        "en": "",
        "ar": "",
        "fr": "",
    },
}


def build_persona_hint(
    profile: Optional["VisionProfile"],
    lang: str,
) -> Optional[str]:
    """Translate a fresh vision profile into a short tone instruction.

    Rules:
    - profile=None or face_detected=False           → no hint
    - source == "disabled"                          → no hint
    - confidence below settings.VISION_*_CONF_MIN   → drop that half
    - if both halves drop                           → no hint
    - lang must be 'en' | 'ar' | 'fr' else default to 'en'

    Returns the joined tone string ready to drop into the system prompt,
    or None to signal "use the default tone — do not mention the visitor's
    appearance at all".
    """
    if profile is None or not profile.face_detected:
        return None
    if profile.source == "disabled":
        return None

    if lang not in ("en", "ar", "fr"):
        lang = "en"

    parts: list[str] = []

    # Age half
    age_ok = (
        profile.age_group is not None
        and profile.age_confidence is not None
        and profile.age_confidence >= settings.VISION_AGE_CONF_MIN
    )
    if age_ok:
        snippet = _AGE_TONE.get(profile.age_group, {}).get(lang, "")
        if snippet:
            parts.append(snippet)

    # Mood half
    mood_ok = (
        profile.mood is not None
        and profile.mood_confidence is not None
        and profile.mood_confidence >= settings.VISION_MOOD_CONF_MIN
    )
    if mood_ok:
        snippet = _MOOD_TONE.get(profile.mood, {}).get(lang, "")
        if snippet:
            parts.append(snippet)

    if not parts:
        return None
    return " ".join(parts)


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
    persona_hint: str | None = None,
) -> str:
    """Ask Gemini for a reply.

    history items are {"role": "user"|"assistant", "content": str}, oldest
    first, NOT including the current message. The current message is
    appended last.

    `persona_hint` is the output of build_persona_hint() — a short string
    in the visitor's language telling THOTH how to adapt tone. Passed as
    None when vision is off or low-confidence; in that case the system
    prompt stays exactly as it was before this feature.
    """
    client = _get_client()

    # Build a single prompt: system rules + exhibit context + history + new turn.
    # We use the simpler "single text blob" form Gemini accepts, since our
    # turn count is small and this keeps the call robust across SDK versions.
    parts: list[str] = [SYSTEM_PROMPT]

    if persona_hint:
        # Important: we tell the model HOW to use the hint (adapt tone) but
        # NOT to mention the visitor's appearance, age, or mood in the reply.
        # That would be creepy.
        parts.append(
            "Adapt your tone based on this observation about the visitor, "
            "but NEVER mention their appearance, age, or mood in the reply: "
            + persona_hint
        )

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

    # Retry transient 503 / overloaded errors with short exponential backoff.
    # Gemini's free tier hits capacity walls under load; most go away in
    # 1-3 seconds. 3 attempts total = up to ~6 s budget — still well under
    # the browser's request timeout.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_message,
            )
            return (response.text or "").strip()
        except Exception as e:
            last_exc = e
            if not _is_transient(e) or attempt == 2:
                raise
            backoff = 1.0 * (attempt + 1)   # 1.0, 2.0
            print(f"[llm] transient error (attempt {attempt+1}/3) -- retrying in {backoff}s: {e}")
            time.sleep(backoff)
    # Unreachable, but satisfies the type checker
    raise last_exc if last_exc else RuntimeError("ask_gemini exhausted retries")

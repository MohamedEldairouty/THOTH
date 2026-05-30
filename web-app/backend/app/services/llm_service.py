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
        # Demo-tuned: deliberately exaggerated so the difference vs the
        # adult/teen baseline is OBVIOUS in a live presentation. The judge
        # should hear it within the first sentence.
        "en": "The visitor is a young child (around 8 years old). Speak like "
              "an excited kids' TV host. Use VERY short, simple sentences. "
              "Sprinkle in words like 'wow', 'amazing', 'super cool'. Use "
              "exclamation marks generously. Compare ancient things to things "
              "a child knows (e.g. 'as tall as ten kids stacked up!'). Keep "
              "the WHOLE reply to 2 short sentences max.",
        "ar": "الزائر طفل صغير في حوالي الثامنة من عمره. تحدث مثل مقدم برامج "
              "أطفال متحمس! استخدم جملًا قصيرة جدًا وبسيطة. أكثر من كلمات مثل "
              "'واو!' و'مذهل!' و'رائع جدًا!'. شبّه الأشياء القديمة بأشياء يعرفها "
              "الطفل. أبقِ الرد كله في جملتين قصيرتين فقط.",
        "fr": "Le visiteur est un jeune enfant (environ 8 ans). Parle comme "
              "un animateur d'émission pour enfants enthousiaste ! Phrases "
              "TRÈS courtes et simples. Utilise des mots comme 'waouh', "
              "'génial', 'super cool'. Beaucoup de points d'exclamation. "
              "Compare les choses anciennes à des choses qu'un enfant connaît. "
              "Maximum 2 phrases courtes pour TOUTE la réponse.",
    },
    "teen": {
        "en": "The visitor is a teenager. Speak like a cool older sibling — "
              "casual, punchy, never preachy. Drop formal vocabulary. Use "
              "phrases like 'pretty wild', 'honestly so cool', 'no joke'. "
              "Keep sentences short and confident. Skip the textbook tone.",
        "ar": "الزائر مراهق. تحدث مثل أخ أكبر رائع — عفوي ومباشر وليس متكلفًا. "
              "تجنب المفردات الرسمية. استخدم تعابير حماسية. أبقِ الجمل قصيرة "
              "وواثقة. تخلَّ عن أسلوب الكتاب المدرسي.",
        "fr": "Le visiteur est un adolescent. Parle comme un grand frère "
              "cool — décontracté, punchy, jamais pédant. Évite le vocabulaire "
              "formel. Utilise des expressions comme 'plutôt dingue', "
              "'franchement cool'. Phrases courtes et assurées. Oublie le ton "
              "manuel scolaire.",
    },
    "adult": {
        # Default tone IS the adult tone. Empty keeps the prompt clean.
        "en": "",
        "ar": "",
        "fr": "",
    },
    "senior": {
        "en": "The visitor is an older adult. Speak with formal courtesy and "
              "calm, measured pacing. Use full, complete sentences — no slang, "
              "no exclamation marks. Address them respectfully (e.g. 'you may "
              "find it interesting that...'). Slightly longer, more reflective "
              "phrasing is welcome.",
        "ar": "الزائر شخص مسنّ. تحدث بأدب رسمي وإيقاع هادئ ومتأنٍ. استخدم جملًا "
              "كاملة ومحترمة، بلا عامية ولا علامات تعجب. خاطبه باحترام. لا بأس "
              "بصياغات أطول قليلًا وأكثر تأملًا.",
        "fr": "Le visiteur est une personne âgée. Parle avec courtoisie "
              "formelle et un rythme calme et posé. Phrases complètes — pas "
              "d'argot, pas de points d'exclamation. Adresse-toi avec respect. "
              "Formulations un peu plus longues et réfléchies bienvenues.",
    },
}

_MOOD_TONE = {
    "happy": {
        "en": "The visitor looks happy and engaged. Match their joy! Be "
              "enthusiastic. Use exclamation marks. Add a fun side fact or "
              "playful comment at the end. Make the reply feel celebratory.",
        "ar": "يبدو الزائر سعيدًا ومتفاعلًا. شاركه بهجته! كن متحمسًا. استخدم "
              "علامات تعجب. أضف معلومة مرحة أو تعليقًا لطيفًا في النهاية.",
        "fr": "Le visiteur a l'air heureux et engagé. Partage sa joie ! Sois "
              "enthousiaste. Utilise des points d'exclamation. Ajoute un fait "
              "amusant ou un commentaire ludique à la fin.",
    },
    "surprise": {
        "en": "The visitor looks surprised or curious — lean into the 'wow' "
              "factor. Open with something hooky like 'Right?!' or 'I know!'. "
              "Feed the curiosity with one extra surprising detail.",
        "ar": "يبدو الزائر متفاجئًا أو فضوليًا — استثمر عنصر الدهشة! ابدأ "
              "بشيء جذاب مثل 'صحيح؟!' أو 'أعرف!'. أشبع فضوله بتفصيل مدهش إضافي.",
        "fr": "Le visiteur semble surpris ou curieux — joue sur l'effet "
              "'waouh'. Ouvre avec quelque chose comme 'Hein, incroyable ?!' "
              "Nourris cette curiosité avec un détail surprenant de plus.",
    },
    "sad": {
        "en": "The visitor seems a little down. Be gentle and warm. NO "
              "exclamation marks. Briefly ask 'Is everything alright?' before "
              "answering. Speak softly, shorter sentences.",
        "ar": "يبدو الزائر متضايقًا قليلًا. كن لطيفًا ودافئًا. لا تستخدم علامات "
              "تعجب. اسأل باختصار 'هل كل شيء على ما يرام؟' قبل الإجابة. تحدث "
              "بهدوء وبجمل أقصر.",
        "fr": "Le visiteur semble un peu triste. Sois doux et chaleureux. "
              "AUCUN point d'exclamation. Demande brièvement 'Tout va bien ?' "
              "avant de répondre. Parle doucement, en phrases courtes.",
    },
    "fear": {
        "en": "The visitor looks uneasy. Speak in a calm, reassuring tone — "
              "the kind a guide uses to settle a nervous visitor. Short, "
              "steady sentences. No surprises, no exclamation marks.",
        "ar": "يبدو الزائر قلقًا. تحدث بنبرة هادئة ومطمئنة — كما يطمئن المرشد "
              "زائرًا متوترًا. جمل قصيرة وثابتة. بدون مفاجآت أو علامات تعجب.",
        "fr": "Le visiteur semble mal à l'aise. Parle d'une voix calme et "
              "rassurante — comme un guide qui apaise un visiteur nerveux. "
              "Phrases courtes et stables. Pas de surprises ni d'exclamations.",
    },
    "angry": {
        # Strongest deviation from default. This is the most "demoable" mood.
        "en": "The visitor looks frustrated or upset. Drop all enthusiasm "
              "IMMEDIATELY. No exclamation marks. No fun facts. No jokes. "
              "Open with a brief acknowledgement like 'Of course.' or "
              "'Certainly.' Then answer in ONE short, factual sentence. "
              "Get straight to the point. Tone: like a calm, respectful "
              "concierge defusing a complaint.",
        "ar": "يبدو الزائر منزعجًا أو متضايقًا. تخلَّ عن أي حماس فورًا. لا علامات "
              "تعجب. لا معلومات ممتعة. لا مزاح. ابدأ باعتراف قصير مثل 'بالتأكيد.' "
              "ثم أجب بجملة واحدة قصيرة ومباشرة. النبرة: مثل موظف استقبال هادئ "
              "ومحترم يهدّئ شكوى.",
        "fr": "Le visiteur a l'air agacé ou contrarié. Abandonne TOUT "
              "enthousiasme immédiatement. Aucun point d'exclamation. Aucun "
              "fait amusant. Aucune blague. Ouvre par une brève reconnaissance "
              "comme 'Bien sûr.' Puis réponds en UNE seule phrase factuelle. "
              "Va droit au but. Ton : comme un concierge calme et respectueux "
              "qui désamorce une plainte.",
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

import asyncio
import base64
import os
import shutil
import subprocess
import tempfile
import time

import numpy as np

# ─────────────────────────────────────────────────────────────
# ffmpeg resolution (Windows-friendly)
# Whisper calls subprocess.run(["ffmpeg", ...]) and on Windows the
# bare name is not always resolved from PATH inside child processes.
# We pick a concrete ffmpeg.exe path and monkey-patch whisper.audio
# so it never relies on PATH lookups.
# ─────────────────────────────────────────────────────────────

def _resolve_ffmpeg() -> str | None:
    # 1) explicit env override
    env = os.environ.get("FFMPEG_BINARY")
    if env and os.path.isfile(env):
        return env
    # 2) PATH lookup
    found = shutil.which("ffmpeg")
    if found:
        return found
    # 3) common Windows install locations
    for p in (r"C:\ffmpeg\bin\ffmpeg.exe", r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"):
        if os.path.isfile(p):
            return p
    return None


FFMPEG_EXE = _resolve_ffmpeg()
if FFMPEG_EXE is None:
    print("[WARNING] ffmpeg not found - Whisper transcription will fail.")
else:
    # Ensure subprocesses can also find it
    ffmpeg_dir = os.path.dirname(FFMPEG_EXE)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import edge_tts
import whisper
import whisper.audio as _whisper_audio

# ── ElevenLabs (primary TTS). Import is best-effort so the backend still
# boots if the SDK isn't installed yet. We just fall back to edge-tts in
# that case.
try:
    from elevenlabs import ElevenLabs   # type: ignore
    _ELEVENLABS_OK = True
except Exception:
    _ELEVENLABS_OK = False

from app.config import settings


def _patched_load_audio(file: str, sr: int = 16000) -> np.ndarray:
    """Replacement for whisper.audio.load_audio using absolute ffmpeg path."""
    if FFMPEG_EXE is None:
        raise RuntimeError("ffmpeg not available")
    cmd = [
        FFMPEG_EXE,
        "-nostdin",
        "-threads", "0",
        "-i", file,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        # Surface a clean error message including ffmpeg's last lines
        raise RuntimeError(
            f"ffmpeg failed to decode audio (exit {result.returncode}). "
            f"Common cause: empty/very short recording. "
            f"Details: {stderr[-400:]}"
        )
    return np.frombuffer(result.stdout, np.int16).flatten().astype(np.float32) / 32768.0


# Apply the patch — whisper will now use the absolute ffmpeg path
if FFMPEG_EXE is not None:
    _whisper_audio.load_audio = _patched_load_audio
    print(f"[OK] Voice service ready (ffmpeg: {FFMPEG_EXE})")

VOICES = {
    "ar": "ar-EG-ShakirNeural",   # Egyptian Arabic — male
    "en": "en-US-GuyNeural",       # US English — male
    "fr": "fr-FR-HenriNeural",     # French — male
}


# ── Pronunciation fixes per language ──────────────────────────────────
# edge-tts reads Arabic without diacritics by guessing vowels. THOTH's
# Arabic name "تحوت" (Tehot/Tahoot) gets collapsed into "Tut" without
# diacritic hints. Adding fatha/damma forces the correct pronunciation.
#
# Apply these substitutions before sending text to the TTS engine; the
# visible text shown in the chat UI is NOT changed.
_PRONUNCIATION_FIXES = {
    "ar": [
        ("تحوت", "تَحُوت"),
        ("توت",  "تَحُوت"),
    ],
    "en": [],
    "fr": [],
}


def _apply_pronunciation_fixes(text: str, language: str) -> str:
    for src, dst in _PRONUNCIATION_FIXES.get(language, []):
        text = text.replace(src, dst)
    return text

_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        size = (settings.WHISPER_MODEL or "base").strip().lower()
        print(f"Loading Whisper model: {size!r}  (first time downloads up to ~1.5GB)...")
        _whisper_model = whisper.load_model(size)
        print(f"Whisper ready ({size}).")
    return _whisper_model


def transcribe_audio(audio_bytes: bytes) -> tuple[str, str]:
    """Transcribe audio bytes → (text, language_code)."""
    print(f"[voice] received {len(audio_bytes)} bytes of audio")

    # Guard: empty / near-empty blobs from a too-short recording
    if len(audio_bytes) < 2000:
        print(f"[voice] rejected -- too short")
        return "", "en"

    suffix = ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        # Pre-decode to check amplitude (catches silent mic)
        try:
            pcm = _patched_load_audio(tmp_path)
            import numpy as _np
            peak = float(_np.max(_np.abs(pcm))) if pcm.size else 0.0
            print(f"[voice] decoded PCM: {pcm.size} samples, peak amplitude={peak:.4f}")
            if peak < 0.005:
                print("[voice] audio is essentially silent -- mic level too low or muted")
                return "", "en"
        except Exception as e:
            print(f"[voice] pre-decode failed: {e}")

        model = get_whisper_model()
        result = model.transcribe(tmp_path)
        text = result["text"].strip()
        lang = result["language"]
        print(f"[voice] whisper -> lang={lang!r}, text={text!r}")
        # Keep the detected lang as-is — chat_service decides whether to TTS.
        # Whisper returns ISO-639-1 codes (e.g. 'ar', 'en', 'fr', 'es', 'de'...)
        return text, lang
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────────────
# ElevenLabs TTS (primary)
# ──────────────────────────────────────────────────────────────────────

_eleven_client = None


def _get_eleven_client():
    """Lazy-init the ElevenLabs client. Returns None if SDK isn't installed
    or API key isn't configured — caller falls back to edge-tts."""
    global _eleven_client
    if _eleven_client is not None:
        return _eleven_client
    if not _ELEVENLABS_OK:
        return None
    if not settings.ELEVENLABS_API_KEY:
        return None
    _eleven_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
    print(f"[tts] ElevenLabs ready (voice={settings.ELEVENLABS_VOICE_ID}, model={settings.ELEVENLABS_MODEL})")
    return _eleven_client


def _elevenlabs_tts_bytes(text: str) -> bytes | None:
    """Synthesize `text` via ElevenLabs and return MP3 bytes, or None on
    any failure (network, quota, API errors, etc.)."""
    client = _get_eleven_client()
    if client is None:
        return None
    try:
        # The SDK returns a streaming iterator of MP3 chunks. Concatenate
        # them — we need the full payload to base64-encode for the frontend.
        audio_iter = client.text_to_speech.convert(
            text=text,
            voice_id=settings.ELEVENLABS_VOICE_ID,
            model_id=settings.ELEVENLABS_MODEL,
            output_format="mp3_44100_128",
        )
        return b"".join(audio_iter)
    except Exception as e:
        print(f"[tts] ElevenLabs error -- will fall back to edge-tts: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────
# edge-tts (fallback so the demo never goes silent)
# ──────────────────────────────────────────────────────────────────────


async def _edge_generate_tts(text: str, language: str, output_path: str) -> None:
    voice = VOICES.get(language, VOICES["en"])
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def _run_edge_tts_in_thread(text: str, language: str, output_path: str) -> None:
    """Run async edge-tts in a fresh event loop on a new thread (FastAPI is
    already inside an event loop, so asyncio.run() would raise)."""
    import threading

    err: list[BaseException] = []

    def _worker():
        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_edge_generate_tts(text, language, output_path))
            finally:
                loop.close()
        except BaseException as e:
            err.append(e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=30)
    if err:
        raise err[0]
    if t.is_alive():
        raise RuntimeError("edge-tts timed out after 30s")


# ──────────────────────────────────────────────────────────────────────
# Public API — used by chat_service / tour_service / navigation_service
# ──────────────────────────────────────────────────────────────────────


def text_to_speech_base64(text: str, language: str) -> str:
    """Convert text to speech, return base64-encoded MP3.

    Order of operations:
      1. Apply Arabic-name diacritic fixes (visible text stays unchanged).
      2. Try ElevenLabs `eleven_multilingual_v2` — a single voice (Bill)
         handles ar/en/fr and any language the model supports. Used in
         the AI team's reference implementation under ai-services/.
      3. If ElevenLabs is unavailable (no key, network error, quota hit),
         fall back to edge-tts with the language-specific male voice from
         the VOICES table. The demo never goes silent.
    """
    if not text or not text.strip():
        return ""

    spoken_text = _apply_pronunciation_fixes(text, language)

    # 1) Primary: ElevenLabs
    audio_bytes = _elevenlabs_tts_bytes(spoken_text)
    if audio_bytes:
        return base64.b64encode(audio_bytes).decode()

    # 2) Fallback: edge-tts (writes to disk, reads it back)
    output_path = os.path.join(tempfile.gettempdir(), f"thoth_tts_{int(time.time() * 1000)}.mp3")
    try:
        _run_edge_tts_in_thread(spoken_text, language, output_path)
        with open(output_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

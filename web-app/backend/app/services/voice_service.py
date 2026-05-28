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
        print("Loading Whisper model... (first time takes ~30s)")
        _whisper_model = whisper.load_model("base")
        print("Whisper ready.")
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


async def _generate_tts(text: str, language: str, output_path: str) -> None:
    voice = VOICES.get(language, VOICES["en"])
    # Pronunciation fixes are applied to the TTS input only; the visible
    # text shown in the chat UI is the original LLM output.
    spoken_text = _apply_pronunciation_fixes(text, language)
    communicate = edge_tts.Communicate(spoken_text, voice)
    await communicate.save(output_path)


def _run_tts_in_thread(text: str, language: str, output_path: str) -> None:
    """Run async edge-tts in a fresh event loop on a new thread.

    Required because text_to_speech_base64 is called from inside FastAPI's
    running event loop, where asyncio.run() raises RuntimeError.
    """
    import threading

    err: list[BaseException] = []

    def _worker():
        try:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_generate_tts(text, language, output_path))
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


def text_to_speech_base64(text: str, language: str) -> str:
    """Convert text to speech and return base64-encoded MP3."""
    if not text or not text.strip():
        return ""
    output_path = os.path.join(tempfile.gettempdir(), f"thoth_tts_{int(time.time() * 1000)}.mp3")
    try:
        _run_tts_in_thread(text, language, output_path)
        with open(output_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

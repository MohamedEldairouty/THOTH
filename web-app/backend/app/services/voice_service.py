import asyncio
import base64
import os
import shutil
import tempfile
import time

# Ensure ffmpeg is reachable on Windows even if PATH was not refreshed
# (Whisper invokes ffmpeg as a subprocess; without this it raises FileNotFoundError)
_FFMPEG_DIR = r"C:\ffmpeg\bin"
if os.name == "nt" and os.path.isdir(_FFMPEG_DIR) and _FFMPEG_DIR not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

if shutil.which("ffmpeg") is None:
    print("⚠ WARNING: ffmpeg not found on PATH — Whisper transcription will fail.")

import edge_tts
import whisper

VOICES = {
    "ar": "ar-EG-SalmaNeural",
    "en": "en-US-JennyNeural",
    "fr": "fr-FR-DeniseNeural",
}

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
    suffix = ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        model = get_whisper_model()
        result = model.transcribe(tmp_path)
        text = result["text"].strip()
        lang = result["language"]
        if lang not in ("ar", "en", "fr"):
            lang = "en"
        return text, lang
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def _generate_tts(text: str, language: str, output_path: str) -> None:
    voice = VOICES.get(language, VOICES["en"])
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_speech_base64(text: str, language: str) -> str:
    """Convert text to speech and return base64-encoded MP3."""
    output_path = os.path.join(tempfile.gettempdir(), f"thoth_tts_{int(time.time())}.mp3")
    try:
        asyncio.run(_generate_tts(text, language, output_path))
        with open(output_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

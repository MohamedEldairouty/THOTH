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
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


# Apply the patch — whisper will now use the absolute ffmpeg path
if FFMPEG_EXE is not None:
    _whisper_audio.load_audio = _patched_load_audio
    print(f"[OK] Voice service ready (ffmpeg: {FFMPEG_EXE})")

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

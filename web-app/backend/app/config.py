from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "dev_secret"
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    GEMINI_API_KEY: str = ""

    # ── ElevenLabs TTS (primary). Leave blank to fall back to edge-tts. ──
    # Sign up at https://elevenlabs.io and grab a key from Profile → API Keys.
    ELEVENLABS_API_KEY: str = ""
    # "Bill" — deep male, multilingual. Same one the AI team picked.
    ELEVENLABS_VOICE_ID: str = "pqHfZKP75CvOlQylNhV4"
    # Multilingual v2 handles ar/en/fr (and many more) in one voice.
    ELEVENLABS_MODEL: str = "eleven_multilingual_v2"

    # Whisper STT model size: tiny | base | small | medium | large
    # "small" gives much better Arabic accuracy than "base" (~460 MB download).
    WHISPER_MODEL: str = "base"

    # ── Vision (age + mood) ──────────────────────────────────────────────
    # When false, /api/vision/analyze short-circuits to "vision disabled"
    # and the chat path skips the tone-hint injection. Useful for kiosks
    # without a camera or privacy-locked deployments.
    VISION_ENABLED: bool = True
    # "auto" picks cuda when available, else cpu. Force "cpu" on the demo
    # laptop if the GPU is busy serving something else.
    VISION_DEVICE: str = "auto"
    # Drop profiles older than this many seconds (LLM ignores stale moods).
    # Demo-tuned at 30s so the presenter can pose → wait → narrate to the
    # audience → then send a chat message and still get the right tone.
    VISION_PROFILE_TTL_S: float = 30.0
    # Minimum age-bucket / mood softmax confidence to actually trust the
    # signal. Below this we drop just that half of the hint (or both).
    # Calibrated against our test accuracies (61% age / 66% mood) so we
    # don't commit to a wrong tone on a coin-flip prediction.
    VISION_AGE_CONF_MIN: float = 0.45
    VISION_MOOD_CONF_MIN: float = 0.45

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()

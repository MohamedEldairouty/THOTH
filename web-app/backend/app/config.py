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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()

"""Every environment variable the service reads, with its default, in one place.

`get_settings()` reads the environment on each call (it is cheap), so tests can
monkeypatch variables without clearing a cache.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # FalkorDB (knowledge graph)
    falkordb_host: str
    falkordb_port: int
    falkordb_graph: str
    # Postgres (sessions, transcripts, handover plans)
    database_url: str
    # LLM and voice providers (OpenRouter)
    openrouter_api_key: str | None
    llm_model: str
    stt_model: str
    tts_model: str
    tts_voice: str
    voice_grace_s: float  # pause allowed before a spoken answer is saved
    # POST /reset erases everything and the API has no auth, so it is off unless asked for
    enable_reset: bool

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv
        return cls(
            falkordb_host=env("FALKORDB_HOST", "localhost"),
            falkordb_port=int(env("FALKORDB_PORT", "6379")),
            falkordb_graph=env("FALKORDB_KT_GRAPH", "knowledge_transfer"),
            database_url=env(
                "DATABASE_URL", "postgresql+asyncpg://kt:kt@localhost:5432/knowledge_transfer"
            ),
            openrouter_api_key=env("OPENROUTER_API_KEY") or None,
            llm_model=env("LLM_MODEL", "openai/gpt-4o-mini"),
            stt_model=env("STT_MODEL", "deepgram/nova-3"),
            tts_model=env("TTS_MODEL", "deepgram/aura-2"),
            tts_voice=env("TTS_VOICE", "aura-2-thalia-en"),
            voice_grace_s=float(env("VOICE_GRACE_S", "0.8")),
            enable_reset=env("ENABLE_RESET", "").lower() in ("1", "true", "yes"),
        )


def get_settings() -> Settings:
    return Settings.from_env()

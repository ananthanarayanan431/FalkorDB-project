"""Every environment variable the service reads, with its default, in one place.

`get_settings()` reads the environment on each call (it is cheap), so tests can
monkeypatch variables without clearing a cache. See `.env.example` at the repository
root for a documented list.
"""
import os
from dataclasses import dataclass
from typing import Literal

Environment = Literal["development", "production"]

DEV_ORIGINS = ("http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:8000", "http://127.0.0.1:8000")


def _flag(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _list(value: str | None, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None or value.strip() == "":
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    # Deployment
    environment: Environment
    log_level: str
    # Interactive API docs (/docs, /openapi.json). Off by default in production.
    enable_docs: bool
    # Host header allowlist; empty accepts any host (development).
    allowed_hosts: tuple[str, ...]
    # Browser origins allowed to open the voice WebSocket.
    allowed_origins: tuple[str, ...]
    # Largest request body accepted, in bytes.
    max_request_bytes: int
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

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv
        environment = env("APP_ENV", "development").strip().lower()
        if environment not in ("development", "production"):
            raise ValueError(f"APP_ENV must be 'development' or 'production', not {environment!r}")
        production = environment == "production"
        return cls(
            environment=environment,  # type: ignore[arg-type]  # checked above
            log_level=env("LOG_LEVEL", "INFO").upper(),
            enable_docs=_flag(env("ENABLE_DOCS"), default=not production),
            allowed_hosts=_list(env("ALLOWED_HOSTS")),
            allowed_origins=_list(env("ALLOWED_ORIGINS"), default=() if production else DEV_ORIGINS),
            max_request_bytes=int(env("MAX_REQUEST_BYTES", str(5 * 1024 * 1024))),
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
            enable_reset=_flag(env("ENABLE_RESET"), default=False),
        )


def get_settings() -> Settings:
    return Settings.from_env()

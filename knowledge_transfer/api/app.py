"""Application factory."""
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from knowledge_transfer.api import v1
from knowledge_transfer.api.deps import Services
from knowledge_transfer.api.errors import register_error_handlers
from knowledge_transfer.api.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from knowledge_transfer.core.config import get_settings
from knowledge_transfer.core.llm import default_llm
from knowledge_transfer.db import make_engine, make_sessionmaker
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.services.assistant import Assistant
from knowledge_transfer.voice.providers import VoiceProviders

log = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    """Send this package's logs to stderr. Leaves logging alone if the host process
    (uvicorn, a test runner) already configured the root logger."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("knowledge_transfer").setLevel(level)


def create_app(services: Services | None = None) -> FastAPI:
    """Build the app. Pass `services` to inject the graph, assistant and database (tests);
    the caller then owns their lifecycle. The Postgres schema is managed by Alembic
    (`make migrate`), not created here."""
    if services is None:
        load_dotenv()  # before reading settings, so .env values apply to the app itself
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.is_production:
        if not settings.allowed_origins:
            log.warning("ALLOWED_ORIGINS is empty: browsers cannot open voice interviews")
        if not settings.allowed_hosts:
            log.warning("ALLOWED_HOSTS is empty: any Host header is accepted")
        if settings.enable_reset:
            log.warning("ENABLE_RESET is on: anyone who can reach the API can delete all data")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is not None:
            yield
            return
        engine = make_engine()
        graph = await KnowledgeGraph.connect()
        voice = VoiceProviders.from_env()
        app.state.services = Services(
            graph, Assistant(default_llm()), make_sessionmaker(engine), voice
        )
        log.info("API started (%s)", settings.environment)
        try:
            yield
        finally:
            if voice:
                await voice.aclose()
            await graph.aclose()
            await engine.dispose()

    app = FastAPI(
        title="Exit-interview knowledge transfer",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )
    if services is not None:
        app.state.services = services
    register_error_handlers(app)
    app.include_router(v1.router)

    # Starlette runs the last-added middleware first: host check, then headers, then size.
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    return app

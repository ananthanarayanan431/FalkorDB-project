"""Application factory."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from knowledge_transfer.api import v1
from knowledge_transfer.api.deps import Services
from knowledge_transfer.api.errors import register_error_handlers
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.llm import default_llm


def create_app(services: Services | None = None) -> FastAPI:
    """Build the app. Pass `services` to inject a graph and assistant (tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is None:
            load_dotenv()
            app.state.services = Services(KnowledgeGraph(), Assistant(default_llm()))
        else:
            app.state.services = services
        yield

    app = FastAPI(title="Exit-interview knowledge transfer", version="1.0.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(v1.router)
    return app

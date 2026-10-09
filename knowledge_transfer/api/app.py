"""Application factory."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from knowledge_transfer.api import v1
from knowledge_transfer.api.deps import Services
from knowledge_transfer.api.errors import register_error_handlers
from knowledge_transfer.assistant import Assistant
from knowledge_transfer.db import make_engine, make_sessionmaker
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.llm import default_llm


def create_app(services: Services | None = None) -> FastAPI:
    """Build the app. Pass `services` to inject the graph, assistant and database (tests);
    the caller then owns their lifecycle. The Postgres schema is managed by Alembic
    (`make migrate`), not created here."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if services is not None:
            yield
            return
        load_dotenv()
        engine = make_engine()
        graph = await KnowledgeGraph.connect()
        app.state.services = Services(graph, Assistant(default_llm()), make_sessionmaker(engine))
        try:
            yield
        finally:
            await graph.aclose()
            await engine.dispose()

    app = FastAPI(title="Exit-interview knowledge transfer", version="1.0.0", lifespan=lifespan)
    if services is not None:
        app.state.services = services
    register_error_handlers(app)
    app.include_router(v1.router)
    return app

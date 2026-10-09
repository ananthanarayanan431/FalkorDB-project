"""Embedded FalkorDB for the graph. Postgres store: SQLite in memory by default, or a
real database when TEST_DATABASE_URL is set (its tables are dropped and recreated)."""
import os

import pytest
from redislite.async_falkordb_client import AsyncFalkorDB
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from knowledge_transfer.db import Base, SqlInterviewStore, make_sessionmaker
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.seed.northwind import BUNDLE
from knowledge_transfer.services.assistant import Assistant
from knowledge_transfer.services.ingest import ingest_sources
from knowledge_transfer.services.interview import InterviewService

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
async def _falkor(tmp_path_factory):
    db = AsyncFalkorDB(str(tmp_path_factory.mktemp("falkor") / "kt.db"))
    yield db
    await db.close()  # redislite's close() also stops the embedded server; aclose() does not


@pytest.fixture
async def graph(_falkor):
    g = await KnowledgeGraph.connect(db=_falkor, graph_name="kt_test")
    await g.reset()
    return g


@pytest.fixture
async def seeded(graph):
    await ingest_sources(graph, BUNDLE)
    return graph


@pytest.fixture
def assistant():
    return Assistant(llm=None)


@pytest.fixture
async def db():
    if TEST_DATABASE_URL:
        engine = create_async_engine(TEST_DATABASE_URL)
    else:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield make_sessionmaker(engine)
    await engine.dispose()


@pytest.fixture
def store(db):
    return SqlInterviewStore(db)


@pytest.fixture
def interviews(seeded, assistant, store):
    return InterviewService(seeded, assistant, store)

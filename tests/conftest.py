import pytest
from redislite.falkordb_client import FalkorDB

from knowledge_transfer.assistant import Assistant
from knowledge_transfer.graph import KnowledgeGraph
from knowledge_transfer.ingest import ingest_sources
from knowledge_transfer.seed.northwind import BUNDLE


@pytest.fixture(scope="session")
def _db(tmp_path_factory):
    return FalkorDB(str(tmp_path_factory.mktemp("falkor") / "kt.db"))


@pytest.fixture
def graph(_db):
    g = KnowledgeGraph(db=_db, graph_name="kt_test")
    g.reset()
    return g


@pytest.fixture
def seeded(graph):
    ingest_sources(graph, BUNDLE)
    return graph


@pytest.fixture
def assistant():
    return Assistant(llm=None)

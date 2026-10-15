"""An HTTP client for the app, wired to the embedded graph and test database."""
import httpx
import pytest
from helpers import V1

from knowledge_transfer.api import Services, create_app


@pytest.fixture
async def services(graph, assistant, db):
    return Services(graph, assistant, db)


@pytest.fixture
async def client(services):
    transport = httpx.ASGITransport(app=create_app(services))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def seeded_client(client):
    assert (await client.post(f"{V1}/ingest/seed")).status_code == 201
    return client

"""Production safeguards: security headers, size limits, production defaults, host checks."""
import httpx
import pytest
from helpers import V1, assert_error

from knowledge_transfer.api import Services, create_app
from knowledge_transfer.api.schemas import MAX_ANSWER_CHARS
from knowledge_transfer.core.config import Settings


def client_for(services: Services, base_url: str = "http://test") -> httpx.AsyncClient:
    """A client for an app built now, so it picks up environment set by the test."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(services)), base_url=base_url)


async def test_security_headers_on_api_responses(client):
    resp = await client.get(f"{V1}/people")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["cache-control"] == "no-store"


async def test_security_headers_on_errors_too(client):
    resp = await client.get(f"{V1}/interviews/nope")
    assert resp.status_code == 404
    assert resp.headers["x-content-type-options"] == "nosniff"


async def test_declared_body_over_limit_is_rejected(services, monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1000")
    async with client_for(services) as c:
        resp = await c.post(f"{V1}/ingest/sources", content=b"{" + b" " * 2000 + b"}",
                            headers={"content-type": "application/json"})
    assert_error(resp, 413, "PAYLOAD_TOO_LARGE")


async def test_streamed_body_over_limit_is_rejected(services, monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1000")

    async def chunks():  # no Content-Length: the size is only known while reading
        for _ in range(10):
            yield b" " * 200

    async with client_for(services) as c:
        resp = await c.post(f"{V1}/ingest/sources", content=chunks(), headers={"content-type": "application/json"})
    assert_error(resp, 413, "PAYLOAD_TOO_LARGE")


async def test_body_under_limit_is_accepted(services, monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1000")
    async with client_for(services) as c:
        resp = await c.post(f"{V1}/people", json={"id": "ana", "name": "Ana"})
    assert resp.status_code == 201


async def test_overlong_answer_is_a_validation_error(seeded_client):
    started = (await seeded_client.post(f"{V1}/interviews", json={})).json()["data"]
    resp = await seeded_client.post(f"{V1}/interviews/{started['interview_id']}/answer",
                                    json={"answer": "x" * (MAX_ANSWER_CHARS + 1)})
    body = assert_error(resp, 422, "VALIDATION_ERROR")
    assert body["error"]["details"][0]["field"] == "body.answer"


async def test_overlong_id_in_bundle_is_a_validation_error(client):
    resp = await client.post(f"{V1}/ingest/sources", json={"people": [{"id": "x" * 201, "name": "X"}]})
    body = assert_error(resp, 422, "VALIDATION_ERROR")
    assert body["error"]["details"][0]["field"] == "body.people.0.id"


async def test_production_hides_docs_and_demo_page(services, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    async with client_for(services) as c:
        assert (await c.get("/openapi.json")).status_code == 404
        assert (await c.get("/docs")).status_code == 404
        assert (await c.get(f"{V1}/voice-demo")).status_code == 404
        assert (await c.get(f"{V1}/health")).status_code == 200


async def test_docs_can_be_enabled_in_production(services, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENABLE_DOCS", "true")
    async with client_for(services) as c:
        assert (await c.get("/openapi.json")).status_code == 200


async def test_unknown_host_is_rejected_when_hosts_are_configured(services, monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "kt.example.com")
    async with client_for(services, base_url="http://evil.example") as c:
        assert (await c.get(f"{V1}/health")).status_code == 400
    async with client_for(services, base_url="http://kt.example.com") as c:
        assert (await c.get(f"{V1}/health")).status_code == 200


def test_production_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for name in ("ENABLE_DOCS", "ALLOWED_ORIGINS", "ENABLE_RESET"):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert s.is_production and not s.enable_docs and s.allowed_origins == () and not s.enable_reset


def test_invalid_environment_is_refused(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    with pytest.raises(ValueError, match="APP_ENV"):
        Settings.from_env()


async def test_relationship_types_are_checked_before_reaching_cypher(seeded):
    with pytest.raises(ValueError, match="Unsupported relationship type"):
        await seeded.link_touch("ravi", "billing-service", rel="OWNS]->(x) DETACH DELETE x //")
    with pytest.raises(ValueError, match="Unsupported relationship type"):
        await seeded.link_items("billing-service", "KNOWS", "invoice-generator")

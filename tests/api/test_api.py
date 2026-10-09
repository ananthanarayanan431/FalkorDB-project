import httpx
import pytest

from knowledge_transfer.api import Services, create_app

V1 = "/api/v1"


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


def assert_error(resp, status, code):
    assert resp.status_code == status
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["message"]
    return body


async def test_health_uses_success_envelope(client):
    resp = await client.get(f"{V1}/health")
    assert resp.status_code == 200
    assert resp.json() == {
        "success": True, "message": "Service is healthy",
        "data": {"status": "ok", "graph": "up", "database": "up", "llm": False},
    }


async def test_health_reports_store_down(client, services, monkeypatch):
    async def down():
        return False

    monkeypatch.setattr(services.graph, "ping", down)
    body = assert_error(await client.get(f"{V1}/health"), 503, "SERVICE_UNAVAILABLE")
    assert body["error"]["details"] == {"graph": "down", "database": "up"}


async def test_unversioned_route_is_not_found(client):
    assert_error(await client.get("/health"), 404, "NOT_FOUND")


async def test_seed_then_gaps_and_coverage(seeded_client):
    gaps = (await seeded_client.get(f"{V1}/gaps")).json()
    assert gaps["success"] is True
    assert "billing-retry-scheduler" in {g["item_id"] for g in gaps["data"]}
    coverage = (await seeded_client.get(f"{V1}/coverage", params={"leaver": "ravi"})).json()
    assert coverage["data"]["leaver"] == "ravi"


async def test_gaps_without_leaver_is_bad_request(client):
    assert_error(await client.get(f"{V1}/gaps"), 400, "BAD_REQUEST")


async def test_unknown_leaver_is_not_found(seeded_client):
    for path in ("/gaps", "/coverage", "/handover/sam"):
        resp = await seeded_client.get(f"{V1}{path}", params={"leaver": "nobody"})
        assert_error(resp, 404, "NOT_FOUND")


async def test_validation_error_lists_fields(client):
    body = assert_error(await client.post(f"{V1}/people", json={"id": "x"}), 422, "VALIDATION_ERROR")
    assert any(d["field"] == "body.name" for d in body["error"]["details"])


async def test_create_person_returns_201(client):
    resp = await client.post(f"{V1}/people", json={"id": "ana", "name": "Ana"})
    assert resp.status_code == 201
    assert resp.json()["data"]["id"] == "ana"


async def test_knows_rejects_unknown_item_without_partial_write(seeded_client, services):
    resp = await seeded_client.put(f"{V1}/people/sam/knows", json=[
        {"item": "billing-service", "level": 3},
        {"item": "nope", "level": 2},
    ])
    body = assert_error(resp, 404, "NOT_FOUND")
    assert body["error"]["details"] == {"missing_items": ["nope"]}
    assert "billing-service" not in await services.graph.knows("sam")


async def test_knows_unknown_person(client):
    assert_error(await client.put(f"{V1}/people/ghost/knows", json=[]), 404, "NOT_FOUND")


async def test_braindump_without_llm_is_unavailable(seeded_client):
    resp = await seeded_client.post(f"{V1}/ingest/braindump", json={"person": "ravi", "text": "I own X"})
    assert_error(resp, 503, "LLM_UNAVAILABLE")


async def test_sources_with_unknown_reference_write_nothing(client):
    bundle = {
        "people": [{"id": "ana", "name": "Ana"}],
        "contributions": [{"person": "ana", "item": "ghost-item"}],
    }
    body = assert_error(await client.post(f"{V1}/ingest/sources", json=bundle), 422, "INVALID_INPUT")
    assert body["error"]["details"] == [
        {"field": "contributions[0].item", "message": "unknown item 'ghost-item'"},
    ]
    assert (await client.get(f"{V1}/graph")).json()["data"]["nodes"] == []


async def test_interview_flow_is_persisted(seeded_client):
    start = await seeded_client.post(f"{V1}/interviews", json={})
    assert start.status_code == 201
    data = start.json()["data"]
    assert data["leaver"] == "ravi" and data["question"]
    iid = data["interview_id"]

    answered = await seeded_client.post(f"{V1}/interviews/{iid}/answer", json={"answer": "Because of X"})
    assert answered.status_code == 200
    assert answered.json()["data"]["stored_for"] == data["question"]["item_id"]

    skipped = await seeded_client.post(f"{V1}/interviews/{iid}/skip")
    assert skipped.status_code == 200 and skipped.json()["success"] is True

    stored = (await seeded_client.get(f"{V1}/interviews/{iid}")).json()["data"]
    assert stored["status"] == "active" and stored["turns"] == 1
    assert [t["action"] for t in stored["transcript"]] == ["answer", "skip"]
    assert stored["transcript"][0]["answer"] == "Because of X"


async def test_answer_after_interview_finished_is_conflict(client):
    await client.post(f"{V1}/people", json={"id": "lee", "name": "Lee", "status": "leaving"})
    iid = (await client.post(f"{V1}/interviews", json={})).json()["data"]["interview_id"]
    assert (await client.get(f"{V1}/interviews/{iid}")).json()["data"]["status"] == "completed"
    resp = await client.post(f"{V1}/interviews/{iid}/answer", json={"answer": "a"})
    assert_error(resp, 409, "CONFLICT")


async def test_unknown_interview(client):
    assert_error(await client.get(f"{V1}/interviews/nope"), 404, "NOT_FOUND")
    assert_error(await client.post(f"{V1}/interviews/nope/skip"), 404, "NOT_FOUND")
    resp = await client.post(f"{V1}/interviews/nope/answer", json={"answer": "a"})
    assert_error(resp, 404, "NOT_FOUND")


async def test_handover_preview_and_unknown_receiver(seeded_client):
    plan = (await seeded_client.get(f"{V1}/handover/sam")).json()
    assert plan["success"] is True and plan["data"]["strategy"] == "foundations-first"
    assert_error(await seeded_client.get(f"{V1}/handover/ghost"), 404, "NOT_FOUND")


async def test_handover_plans_are_saved_and_listed(seeded_client):
    created = await seeded_client.post(f"{V1}/handover-plans", json={"receiver": "sam"})
    assert created.status_code == 201
    saved = created.json()["data"]
    assert saved["receiver"] == "sam" and saved["leaver"] == "ravi"
    assert saved["step_count"] == len(saved["plan"]["steps"]) > 0 and saved["created_at"]
    await seeded_client.post(f"{V1}/handover-plans", json={"receiver": "priya"})

    fetched = (await seeded_client.get(f"{V1}/handover-plans/{saved['id']}")).json()["data"]
    assert fetched == saved

    listed = (await seeded_client.get(f"{V1}/handover-plans", params={"receiver": "sam"})).json()
    assert [p["id"] for p in listed["data"]] == [saved["id"]]
    assert "plan" not in listed["data"][0]  # list returns summaries
    everyone = (await seeded_client.get(f"{V1}/handover-plans")).json()["data"]
    assert {p["receiver"] for p in everyone} == {"sam", "priya"}


async def test_handover_plan_errors(seeded_client):
    resp = await seeded_client.get(f"{V1}/handover-plans/00000000-0000-0000-0000-000000000000")
    assert_error(resp, 404, "NOT_FOUND")
    assert_error(await seeded_client.get(f"{V1}/handover-plans/not-a-uuid"), 422, "VALIDATION_ERROR")
    resp = await seeded_client.post(f"{V1}/handover-plans", json={"receiver": "ghost"})
    assert_error(resp, 404, "NOT_FOUND")


async def test_reset_clears_graph_and_stored_results(seeded_client):
    iid = (await seeded_client.post(f"{V1}/interviews", json={})).json()["data"]["interview_id"]
    await seeded_client.post(f"{V1}/handover-plans", json={"receiver": "sam"})
    resp = await seeded_client.post(f"{V1}/reset")
    assert resp.json() == {"success": True, "message": "Graph, interviews and handover plans reset", "data": None}
    assert (await seeded_client.get(f"{V1}/graph")).json()["data"]["nodes"] == []
    assert_error(await seeded_client.get(f"{V1}/interviews/{iid}"), 404, "NOT_FOUND")
    assert (await seeded_client.get(f"{V1}/handover-plans")).json()["data"] == []


async def test_openapi_documents_error_envelope(client):
    schema = (await client.get("/openapi.json")).json()
    assert "ErrorResponse" in schema["components"]["schemas"]

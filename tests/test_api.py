import pytest
from fastapi.testclient import TestClient

from knowledge_transfer.api import Services, create_app

V1 = "/api/v1"


@pytest.fixture
def client(graph, assistant):
    with TestClient(create_app(Services(graph, assistant))) as c:
        yield c


@pytest.fixture
def seeded_client(client):
    assert client.post(f"{V1}/ingest/seed").status_code == 201
    return client


def assert_error(resp, status, code):
    assert resp.status_code == status
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["message"]
    return body


def test_health_uses_success_envelope(client):
    resp = client.get(f"{V1}/health")
    assert resp.status_code == 200
    assert resp.json() == {
        "success": True, "message": "Service is healthy", "data": {"status": "ok", "llm": False},
    }


def test_unversioned_route_is_not_found(client):
    assert_error(client.get("/health"), 404, "NOT_FOUND")


def test_seed_then_gaps_and_coverage(seeded_client):
    gaps = seeded_client.get(f"{V1}/gaps").json()
    assert gaps["success"] is True
    assert "billing-retry-scheduler" in {g["item_id"] for g in gaps["data"]}
    coverage = seeded_client.get(f"{V1}/coverage", params={"leaver": "ravi"}).json()
    assert coverage["data"]["leaver"] == "ravi"


def test_gaps_without_leaver_is_bad_request(client):
    assert_error(client.get(f"{V1}/gaps"), 400, "BAD_REQUEST")


def test_validation_error_lists_fields(client):
    body = assert_error(client.post(f"{V1}/people", json={"id": "x"}), 422, "VALIDATION_ERROR")
    assert any(d["field"] == "body.name" for d in body["error"]["details"])


def test_create_person_returns_201(client):
    resp = client.post(f"{V1}/people", json={"id": "ana", "name": "Ana"})
    assert resp.status_code == 201
    assert resp.json()["data"]["id"] == "ana"


def test_knows_rejects_unknown_item_without_partial_write(seeded_client):
    resp = seeded_client.put(f"{V1}/people/sam/knows", json=[
        {"person": "sam", "item": "billing-service", "level": 3},
        {"person": "sam", "item": "nope", "level": 2},
    ])
    body = assert_error(resp, 404, "NOT_FOUND")
    assert body["error"]["details"] == {"missing_items": ["nope"]}
    assert "billing-service" not in seeded_client.app.state.services.graph.knows("sam")


def test_knows_unknown_person(client):
    assert_error(client.put(f"{V1}/people/ghost/knows", json=[]), 404, "NOT_FOUND")


def test_braindump_without_llm_is_unavailable(seeded_client):
    resp = seeded_client.post(f"{V1}/ingest/braindump", json={"person": "ravi", "text": "I own X"})
    assert_error(resp, 503, "SERVICE_UNAVAILABLE")


def test_interview_flow(seeded_client):
    start = seeded_client.post(f"{V1}/interviews", json={})
    assert start.status_code == 201
    data = start.json()["data"]
    assert data["leaver"] == "ravi" and data["question"]
    iid = data["interview_id"]

    answered = seeded_client.post(f"{V1}/interviews/{iid}/answer", json={"answer": "Because of X"})
    assert answered.status_code == 200
    assert answered.json()["data"]["stored_for"] == data["question"]["item_id"]

    skipped = seeded_client.post(f"{V1}/interviews/{iid}/skip")
    assert skipped.status_code == 200 and skipped.json()["success"] is True


def test_unknown_interview(client):
    assert_error(client.post(f"{V1}/interviews/nope/skip"), 404, "NOT_FOUND")
    assert_error(client.post(f"{V1}/interviews/nope/answer", json={"answer": "a"}), 404, "NOT_FOUND")


def test_handover_plan_and_unknown_receiver(seeded_client):
    plan = seeded_client.get(f"{V1}/handover/sam").json()
    assert plan["success"] is True and plan["data"]["strategy"] == "foundations-first"
    assert_error(seeded_client.get(f"{V1}/handover/ghost"), 404, "NOT_FOUND")


def test_reset(seeded_client):
    resp = seeded_client.post(f"{V1}/admin/reset")
    assert resp.json() == {"success": True, "message": "Graph and interview sessions reset", "data": None}
    assert seeded_client.get(f"{V1}/graph").json()["data"]["nodes"] == []


def test_openapi_documents_error_envelope(client):
    schema = client.get("/openapi.json").json()
    assert "ErrorResponse" in schema["components"]["schemas"]

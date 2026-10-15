"""The graph explorer endpoints: /graph/schema, /graph/snapshot, /graph/nodes/{id}/neighbors."""
from helpers import V1, assert_error


async def test_schema_counts_labels_and_types(seeded_client):
    data = (await seeded_client.get(f"{V1}/graph/schema")).json()["data"]
    labels = {r["label"]: r["count"] for r in data["labels"]}
    types = {r["type"]: r["count"] for r in data["relationship_types"]}
    assert labels["Person"] == 4
    assert labels["Item"] == labels["System"] + labels["Decision"] + labels["Topic"]
    assert data["node_count"] == labels["Person"] + labels["Item"] + labels["Document"]
    assert data["edge_count"] == sum(types.values())
    assert {"WORKED_ON", "DEPENDS_ON", "PREREQUISITE_OF", "DOCUMENTED_BY", "KNOWS"} <= types.keys()


async def test_schema_of_empty_graph(client):
    data = (await client.get(f"{V1}/graph/schema")).json()["data"]
    assert data == {"node_count": 0, "edge_count": 0, "labels": [], "relationship_types": []}


async def test_snapshot_returns_every_property_and_edge(seeded_client):
    schema = (await seeded_client.get(f"{V1}/graph/schema")).json()["data"]
    snap = (await seeded_client.get(f"{V1}/graph/snapshot")).json()["data"]
    assert snap["truncated"] is False
    assert len(snap["nodes"]) == schema["node_count"]
    assert len(snap["edges"]) == schema["edge_count"]

    ravi = next(n for n in snap["nodes"] if n["properties"].get("id") == "ravi")
    assert ravi["labels"] == ["Person"]
    assert ravi["properties"] == {"id": "ravi", "name": "Ravi Menon", "role": "Senior Backend Engineer",
                                  "seniority": "senior", "status": "leaving"}
    ids = {n["id"] for n in snap["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in snap["edges"])
    worked = next(e for e in snap["edges"] if e["type"] == "WORKED_ON")
    assert {"source", "source_ref", "confidence", "created_at"} <= worked["properties"].keys()


async def test_snapshot_filters_by_label_and_keeps_edges_inside_the_selection(seeded_client):
    snap = (await seeded_client.get(f"{V1}/graph/snapshot", params={"labels": ["Person"]})).json()["data"]
    assert len(snap["nodes"]) == 4
    assert all(n["labels"] == ["Person"] for n in snap["nodes"])
    assert snap["edges"] == []  # people are only linked to items, which are filtered out

    both = (await seeded_client.get(f"{V1}/graph/snapshot", params={"labels": ["Person", "Decision"]})).json()["data"]
    assert {e["type"] for e in both["edges"]} <= {"OWNS", "WORKED_ON", "AUTHORED", "KNOWS"}
    assert len(both["edges"]) > 0


async def test_snapshot_limit_marks_truncation(seeded_client):
    resp = await seeded_client.get(f"{V1}/graph/snapshot", params={"limit": 3})
    snap = resp.json()["data"]
    assert len(snap["nodes"]) == 3
    assert snap["truncated"] is True
    assert "first 3 nodes" in resp.json()["message"]


async def test_snapshot_rejects_bad_limit(client):
    assert_error(await client.get(f"{V1}/graph/snapshot", params={"limit": 0}), 422, "VALIDATION_ERROR")
    assert_error(await client.get(f"{V1}/graph/snapshot", params={"limit": 5001}), 422, "VALIDATION_ERROR")


async def test_neighbors_in_both_directions(seeded_client):
    snap = (await seeded_client.get(f"{V1}/graph/snapshot")).json()["data"]
    billing = next(n for n in snap["nodes"] if n["properties"].get("id") == "billing-service")
    expected = [e for e in snap["edges"] if billing["id"] in (e["source"], e["target"])]

    data = (await seeded_client.get(f"{V1}/graph/nodes/{billing['id']}/neighbors")).json()["data"]
    assert data["truncated"] is False
    assert sorted(e["id"] for e in data["edges"]) == sorted(e["id"] for e in expected)
    assert any(e["target"] == billing["id"] for e in data["edges"])  # incoming
    assert any(e["source"] == billing["id"] for e in data["edges"])  # outgoing
    node_ids = {n["id"] for n in data["nodes"]}
    assert billing["id"] in node_ids
    assert node_ids == {billing["id"]} | {e["source"] for e in expected} | {e["target"] for e in expected}


async def test_neighbors_limit_marks_truncation(seeded_client):
    snap = (await seeded_client.get(f"{V1}/graph/snapshot")).json()["data"]
    ravi = next(n for n in snap["nodes"] if n["properties"].get("id") == "ravi")
    data = (await seeded_client.get(f"{V1}/graph/nodes/{ravi['id']}/neighbors", params={"limit": 1})).json()["data"]
    assert len(data["edges"]) == 1
    assert data["truncated"] is True


async def test_neighbors_unknown_node(client):
    assert_error(await client.get(f"{V1}/graph/nodes/999999/neighbors"), 404, "NOT_FOUND")
    assert_error(await client.get(f"{V1}/graph/nodes/-1/neighbors"), 422, "VALIDATION_ERROR")

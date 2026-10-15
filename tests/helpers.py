"""Shared assertions for the HTTP API tests."""
V1 = "/api/v1"


def assert_error(resp, status, code):
    assert resp.status_code == status
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["message"]
    return body

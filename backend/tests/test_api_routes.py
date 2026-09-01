"""Route registration for SAD §4."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_sad_section_4_paths_respond() -> None:
    # TestClient runs lifespan (Alembic upgrade head) against local DATABASE_URL.
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        ready = client.get("/ready")
        assert ready.status_code in (200, 503)
        unauth = client.post("/api/v1/instances", json={"ticket_system": "jira", "ticket_id": "JIRA-102"})
        assert unauth.status_code == 401
        body = unauth.json()
        assert body["error"]["code"] == "unauthenticated"
        assert client.get("/api/v1/instances").status_code == 401
        assert client.get("/api/v1/instances/ARLO-1").status_code == 401
        assert client.get("/api/v1/instances/ARLO-1/audit").status_code == 401
        assert client.post("/api/v1/instances/ARLO-1/approve", json={"proposal_hash": "x"}).status_code == 401
        assert client.post("/api/v1/instances/ARLO-1/reject", json={"proposal_hash": "x"}).status_code == 401

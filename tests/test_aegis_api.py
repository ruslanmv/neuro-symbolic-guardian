from fastapi.testclient import TestClient

from aegis.api.app import app


def test_healthz():
    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_endpoint():
    client = TestClient(app)
    r = client.post("/verify", json={"text": "consume 3 from 2", "facts": {"inventory": 2}})
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] in {"revise", "deny"}

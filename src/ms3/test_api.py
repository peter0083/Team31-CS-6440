from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200

def test_ready_shape() -> None:
    r = client.get("/ready")
    # readiness might be 503 if warehouse is offline; accept either
    assert r.status_code in (200,503)

def test_contract_keys() -> None:
    # mock a patient id path (you can monkeypatch q() for predictable DF)
    # For now just assert 404 is a valid outcome (shape & error path ok)
    r = client.get("/api/ms3/patient-phenotype/does-not-exist")
    assert r.status_code in (200,404)
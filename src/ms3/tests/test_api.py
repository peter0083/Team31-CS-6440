from typing import Final

import requests

BASE: Final = "http://localhost:8001"

def test_live() -> None:
    r = requests.get(f"{BASE}/live", timeout=5)
    assert r.status_code == 200

def test_ready_or_503() -> None:
    r = requests.get(f"{BASE}/ready", timeout=5)
    assert r.status_code in (200, 503)

def test_patient_example_contract() -> None:
    r = requests.get(f"{BASE}/api/ms3/patient-phenotype/patient-001", timeout=10)
    assert r.status_code in (200, 404)

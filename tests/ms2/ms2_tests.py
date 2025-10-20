"""Tests for MS2 microservice: clinical trial criteria parser."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.ms2.ms2_routes import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


def test_root() -> None:
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MS2 Microservice"
    assert data["status"] == "running"


def test_health_check() -> None:
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_process_data() -> None:
    """Test process endpoint with valid data."""
    payload = {"name": "test_item", "value": 42, "description": "Test description"}
    response = client.post("/api/v1/process", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_item"
    assert data["value"] == 42
    assert data["status"] == "processed"


def test_process_data_invalid() -> None:
    """Test process endpoint with invalid data."""
    payload = {"name": "", "value": 42}
    response = client.post("/api/v1/process", json=payload)
    assert response.status_code == 422  # Validation error


def test_get_items() -> None:
    """Test get all items endpoint."""
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_item_by_id() -> None:
    """Test get specific item endpoint."""
    # First create an item
    payload = {"name": "test_item", "value": 100}
    create_response = client.post("/api/v1/process", json=payload)
    item_id = create_response.json()["id"]

    # Then retrieve it
    response = client.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["name"] == "test_item"


def test_get_item_not_found() -> None:
    """Test get item with non-existent ID."""
    response = client.get("/api/v1/items/99999")
    assert response.status_code == 404


def test_parse_criteria_valid() -> None:
    """Test parse criteria endpoint with valid data."""
    nct_id = "NCT05123456"
    raw_text = (
        "Inclusion Criteria:\n1. Age 18-65 years\n2. Diagnosed Type 2 diabetes\n3."
    )
    payload = {"raw_text": raw_text}
    response = client.post(f"/api/ms2/parse-criteria/{nct_id}", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nct_id"] == nct_id
    assert isinstance(data["parsing_timestamp"], str)
    assert len(data["inclusion_criteria"]) > 0
    assert len(data["exclusion_criteria"]) >= 0
    assert 0.9 < data["parsing_confidence"] <= 1.0
    assert data["total_rules_extracted"] == len(data["inclusion_criteria"]) + len(
        data["exclusion_criteria"]
    )


def test_parse_criteria_invalid() -> None:
    """Test parse criteria endpoint with invalid data."""
    nct_id = "NCT05123456"
    raw_text = ""
    payload = {"raw_text": raw_text}
    response = client.post(f"/api/ms2/parse-criteria/{nct_id}", json=payload)
    assert response.status_code == 400
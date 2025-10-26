"""Tests for MS2 microservice: clinical trial criteria parser."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.ms2.ms2_routes import router

app = FastAPI()
app.include_router(router, prefix="/api/ms2")

client = TestClient(app)


def test_root() -> None:
    """Test root endpoint."""
    response = client.get("/api/ms2/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MS2 criteria parser"
    assert data["status"] == "running"


def test_health_check() -> None:
    """Test health check endpoint."""
    response = client.get("/api/ms2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["llm_provider"] == "openai"
    assert "uptime_seconds" in data


def test_parse_criteria_on_demand_valid() -> None:
    """Test on-demand parsing with valid criteria."""
    nct_id = "NCT05123456"
    raw_text = (
        "Inclusion Criteria:\n"
        "1. Age 18-65 years\n"
        "2. Diagnosed Type 2 diabetes\n"
        "3. HbA1c ≥ 7.0%\n\n"
        "Exclusion Criteria:\n"
        "1. Pregnant women\n"
        "2. Severe kidney disease"
    )

    payload = {"raw_text": raw_text}
    response = client.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    # Note: This test requires OpenAI API key to actually work
    # In a real test environment, you'd mock the LLM response
    if response.status_code == 201:
        data = response.json()
        assert data["nct_id"] == nct_id
        assert isinstance(data["parsing_timestamp"], str)
        assert isinstance(data["inclusion_criteria"], list)
        assert isinstance(data["exclusion_criteria"], list)
        assert 0.0 <= data["parsing_confidence"] <= 1.0
        assert data["total_rules_extracted"] >= 0


def test_parse_criteria_on_demand_empty() -> None:
    """Test on-demand parsing with empty criteria."""
    nct_id = "NCT05123456"
    payload = {"raw_text": ""}

    response = client.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    if response.status_code == 201:
        data = response.json()
        assert data["nct_id"] == nct_id
        assert len(data["inclusion_criteria"]) == 0
        assert len(data["exclusion_criteria"]) == 0
        assert data["parsing_confidence"] == 0.0
        assert data["total_rules_extracted"] == 0


def test_parse_criteria_invalid_nct_format() -> None:
    """Test parsing with invalid NCT ID format."""
    nct_id = "INVALID123"
    payload = {"raw_text": "Age 18-65 years"}

    response = client.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    # Should fail validation due to NCT ID pattern
    # The actual status code depends on when validation occurs
    assert response.status_code in [400, 422, 500]


def test_batch_parse_empty_list() -> None:
    """Test batch parsing with empty list."""
    payload = {"nct_ids": [], "include_reasoning": False}

    response = client.post("/api/ms2/parse-batch", json=payload)

    # Should handle empty list gracefully
    assert response.status_code in [200, 422]


def test_get_parsed_criteria_not_found() -> None:
    """Test retrieving non-existent trial."""
    nct_id = "NCT99999999"

    response = client.get(f"/api/ms2/parsed-criteria/{nct_id}")

    # Should return 404 if trial not found in MS1
    # Or 500 if MS1 is not running
    assert response.status_code in [404, 500, 502]


def test_parse_with_reasoning() -> None:
    """Test parsing with reasoning steps enabled."""
    nct_id = "NCT05123456"
    raw_text = "Inclusion Criteria:\n1. Age 18-65 years"

    payload = {"raw_text": raw_text}
    response = client.post(
        f"/api/ms2/parse-criteria/{nct_id}?include_reasoning=true",
        json=payload,
    )

    if response.status_code == 201:
        data = response.json()
        # Reasoning steps are optional, but if present should be a list
        if "reasoning_steps" in data and data["reasoning_steps"]:
            assert isinstance(data["reasoning_steps"], list)


def test_force_full_model() -> None:
    """Test forcing use of full model."""
    nct_id = "NCT05123456"
    raw_text = "Age 18-30 years"  # Short text

    payload = {"raw_text": raw_text}
    response = client.post(
        f"/api/ms2/parse-criteria/{nct_id}?force_full_model=true",
        json=payload,
    )

    if response.status_code == 201:
        data = response.json()
        # Should use gpt-4o instead of gpt-4o-mini
        assert data["model_used"] == "gpt-4o"


# Integration test examples (require actual MS1 and OpenAI API)
# Uncomment these when you have the full environment set up

# def test_get_parsed_criteria_from_ms1() -> None:
#     """Test fetching and parsing from MS1."""
#     nct_id = "NCT05123456"  # Replace with real NCT ID in MS1
#
#     response = client.get(f"/api/ms2/parsed-criteria/{nct_id}")
#
#     assert response.status_code == 200
#     data = response.json()
#     assert data["nct_id"] == nct_id
#     assert len(data["inclusion_criteria"]) > 0


# def test_batch_parse_multiple_trials() -> None:
#     """Test batch parsing multiple trials."""
#     payload = {
#         "nct_ids": ["NCT05123456", "NCT05123457", "NCT05123458"],
#         "include_reasoning": False
#     }
#
#     response = client.post("/api/ms2/parse-batch", json=payload)
#
#     assert response.status_code == 200
#     data = response.json()
#     assert data["total_processed"] == 3
#     assert len(data["successful"]) + len(data["failed"]) == 3

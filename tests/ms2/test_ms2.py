"""Tests for MS2 microservice with MOCKED OpenAI API calls.

no real API calls to Open AI are made to save costs
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ms2.ms2_pydantic_models import (
    ExclusionCriteriaRule,
    InclusionCriteriaRule,
    ParsedCriteriaResponse,
    ReasoningStep,
)

# ============================================================================
# Fixtures and Mock Data
# ============================================================================

@pytest.fixture
def mock_llm_response():
    """Mock response from LLM parsing."""
    return ParsedCriteriaResponse(
        nct_id="NCT05123456",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[
            InclusionCriteriaRule(
                rule_id="inc_001",
                type="demographic",
                identifier=["age"],
                field="age",
                operator=">=",
                value="18",
                unit="years",
                description="Age 18 to 65 years",
                raw_text="Age 18 to 65 years",
                confidence=0.95,
            ),
            InclusionCriteriaRule(
                rule_id="inc_002",
                type="condition",
                identifier=["diabetes", "type 2"],
                field="diagnosis",
                operator="==",
                value="Type 2 Diabetes",
                unit=None,
                description="Diagnosed with Type 2 Diabetes",
                raw_text="Diagnosed with Type 2 Diabetes",
                confidence=0.92,
                code_system="ICD-10",
                code="E11",
            ),
        ],
        exclusion_criteria=[
            ExclusionCriteriaRule(
                rule_id="exc_001",
                type="demographic",
                identifier=["pregnancy"],
                field="pregnancy_status",
                operator="==",
                value="pregnant",
                unit=None,
                description="Pregnant or breastfeeding",
                raw_text="Pregnant or breastfeeding",
                confidence=0.98,
            ),
        ],
        parsing_confidence=0.95,
        total_rules_extracted=3,
        model_used="gpt-4o-mini",
        reasoning_steps=None,
    )


@pytest.fixture
def mock_diabetes_response():
    """Mock response for diabetes study."""
    return ParsedCriteriaResponse(
        nct_id="NCT05999001",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[
            InclusionCriteriaRule(
                rule_id="inc_001",
                type="demographic",
                identifier=["age"],
                field="age",
                operator="between",
                value="18-65",
                unit="years",
                description="Age 18 to 65 years",
                raw_text="Age 18 to 65 years",
                confidence=0.98,
            ),
            InclusionCriteriaRule(
                rule_id="inc_002",
                type="condition",
                identifier=["type 2 diabetes"],
                field="diagnosis",
                operator="==",
                value="Type 2 Diabetes Mellitus",
                unit=None,
                description="Diagnosed with Type 2 Diabetes Mellitus",
                raw_text="Diagnosed with Type 2 Diabetes Mellitus",
                confidence=0.96,
                code_system="ICD-10",
                code="E11",
            ),
            InclusionCriteriaRule(
                rule_id="inc_003",
                type="lab_value",
                identifier=["HbA1c"],
                field="HbA1c",
                operator="between",
                value="7.0-10.0",
                unit="%",
                description="HbA1c between 7.0% and 10.0%",
                raw_text="HbA1c between 7.0% and 10.0%",
                confidence=0.94,
            ),
        ],
        exclusion_criteria=[
            ExclusionCriteriaRule(
                rule_id="exc_001",
                type="condition",
                identifier=["heart failure"],
                field="heart_failure",
                operator="==",
                value="NYHA Class III or IV",
                unit=None,
                description="History of heart failure (NYHA Class III or IV)",
                raw_text="History of heart failure (NYHA Class III or IV)",
                confidence=0.92,
                code_system="ICD-10",
                code="I50",
            ),
        ],
        parsing_confidence=0.95,
        total_rules_extracted=4,
        model_used="gpt-4o-mini",
        reasoning_steps=None,
    )


@pytest.fixture
def mock_empty_response():
    """Mock response for empty criteria."""
    return ParsedCriteriaResponse(
        nct_id="NCT05999004",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[],
        exclusion_criteria=[],
        parsing_confidence=0.0,
        total_rules_extracted=0,
        model_used="none",
        reasoning_steps=None,
    )


@pytest.fixture
def client_with_mocked_llm(mock_llm_response):
    """Create test client with mocked LLM."""
    with patch("src.ms2.ms2_main.instructor.from_openai") as mock_instructor:
        # Create mock client with async methods
        mock_client = MagicMock()
        mock_completions = AsyncMock()
        mock_completions.create = AsyncMock(return_value=mock_llm_response)
        mock_client.chat.completions = mock_completions
        mock_instructor.return_value = mock_client
        
        # Import and create app after mocking
        from src.ms2.ms2_main import create_app
        app = create_app()
        
        with TestClient(app) as test_client:
            yield test_client


# ============================================================================
# Basic Endpoint Tests
# ============================================================================

def test_root(client_with_mocked_llm):
    """Test root endpoint."""
    response = client_with_mocked_llm.get("/api/ms2/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MS2 criteria parser"
    assert data["status"] == "running"


def test_health_check(client_with_mocked_llm):
    """Test health check endpoint."""
    response = client_with_mocked_llm.get("/api/ms2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["llm_provider"] == "openai"
    assert "uptime_seconds" in data


# ============================================================================
# Mocked Parsing Tests
# ============================================================================

@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_direct_simple_mocked(mock_parse, client_with_mocked_llm, mock_llm_response):
    """Test direct parsing with simple criteria (mocked LLM)."""
    mock_parse.return_value = mock_llm_response
    
    nct_id = "NCT05123456"
    raw_text = """
    Inclusion Criteria:
    - Age 18 to 65 years
    - Diagnosed with Type 2 Diabetes
    
    Exclusion Criteria:
    - Pregnant or breastfeeding
    """

    payload = {"raw_text": raw_text}
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["nct_id"] == nct_id
    assert len(data["inclusion_criteria"]) == 2
    assert len(data["exclusion_criteria"]) == 1
    assert data["total_rules_extracted"] == 3
    assert data["parsing_confidence"] == 0.95
    assert data["model_used"] == "gpt-4o-mini"


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_direct_diabetes_study_mocked(
    mock_parse, client_with_mocked_llm, mock_diabetes_response
):
    """Test parsing a realistic diabetes study criteria (mocked)."""
    mock_parse.return_value = mock_diabetes_response
    
    nct_id = "NCT05999001"
    raw_text = """
    Inclusion Criteria:
    1. Age 18 to 65 years
    2. Diagnosed with Type 2 Diabetes Mellitus for at least 6 months
    3. HbA1c between 7.0% and 10.0%
    """

    payload = {"raw_text": raw_text}
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    
    # Validate response structure
    assert data["nct_id"] == nct_id
    assert len(data["inclusion_criteria"]) == 3
    assert len(data["exclusion_criteria"]) == 1
    
    # Check first rule
    first_rule = data["inclusion_criteria"][0]
    assert first_rule["rule_id"] == "inc_001"
    assert first_rule["type"] == "demographic"
    assert first_rule["confidence"] == 0.98
    
    # Check medical coding
    diabetes_rule = data["inclusion_criteria"][1]
    assert diabetes_rule["code_system"] == "ICD-10"
    assert diabetes_rule["code"] == "E11"


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_direct_empty_mocked(mock_parse, client_with_mocked_llm, mock_empty_response):
    """Test parsing with empty criteria text (mocked)."""
    mock_parse.return_value = mock_empty_response
    
    nct_id = "NCT05999004"
    payload = {"raw_text": ""}

    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["nct_id"] == nct_id
    assert len(data["inclusion_criteria"]) == 0
    assert len(data["exclusion_criteria"]) == 0
    assert data["parsing_confidence"] == 0.0
    assert data["total_rules_extracted"] == 0
    assert data["model_used"] == "none"


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_with_reasoning_mocked(mock_parse, client_with_mocked_llm):
    """Test parsing with reasoning steps enabled (mocked)."""
    mock_response = ParsedCriteriaResponse(
        nct_id="NCT05999003",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[
            InclusionCriteriaRule(
                rule_id="inc_001",
                type="demographic",
                identifier=["age"],
                field="age",
                operator="between",
                value="18-50",
                unit="years",
                description="Adults aged 18-50",
                raw_text="Adults aged 18-50",
                confidence=0.98,
            ),
        ],
        exclusion_criteria=[],
        parsing_confidence=0.95,
        total_rules_extracted=1,
        model_used="gpt-4o-mini",
        reasoning_steps=[
            ReasoningStep(
                step=1,
                description="Identified age criterion in inclusion criteria",
                confidence=0.98,
            ),
            ReasoningStep(
                step=2,
                description="Extracted age range 18-50 years",
                confidence=0.97,
            ),
        ],
    )
    mock_parse.return_value = mock_response
    
    nct_id = "NCT05999003"
    raw_text = "Inclusion: Adults aged 18-50"

    payload = {"raw_text": raw_text}
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}?include_reasoning=true",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    
    # Check reasoning steps
    assert "reasoning_steps" in data
    assert data["reasoning_steps"] is not None
    assert len(data["reasoning_steps"]) == 2
    assert data["reasoning_steps"][0]["step"] == 1


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_whitespace_only_mocked(mock_parse, client_with_mocked_llm, mock_empty_response):
    """Test parsing with only whitespace (mocked)."""
    mock_parse.return_value = mock_empty_response
    
    nct_id = "NCT05999005"
    payload = {"raw_text": "   \n\n   \t  "}

    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["total_rules_extracted"] == 0


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_complex_lab_values_mocked(mock_parse, client_with_mocked_llm):
    """Test parsing criteria with complex lab values and ranges (mocked)."""
    mock_response = ParsedCriteriaResponse(
        nct_id="NCT05999006",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[
            InclusionCriteriaRule(
                rule_id="inc_001",
                type="lab_value",
                identifier=["HbA1c"],
                field="HbA1c",
                operator="between",
                value="7.0-10.0",
                unit="%",
                description="Hemoglobin A1c (HbA1c) ≥ 7.0% and ≤ 10.0%",
                raw_text="Hemoglobin A1c (HbA1c) ≥ 7.0% and ≤ 10.0%",
                confidence=0.96,
            ),
            InclusionCriteriaRule(
                rule_id="inc_002",
                type="lab_value",
                identifier=["eGFR"],
                field="eGFR",
                operator=">=",
                value="60",
                unit="mL/min/1.73m²",
                description="eGFR ≥ 60 mL/min/1.73m²",
                raw_text="eGFR ≥ 60 mL/min/1.73m²",
                confidence=0.95,
            ),
        ],
        exclusion_criteria=[
            ExclusionCriteriaRule(
                rule_id="exc_001",
                type="lab_value",
                identifier=["creatinine"],
                field="creatinine",
                operator=">",
                value="1.5",
                unit="mg/dL",
                description="Creatinine > 1.5 mg/dL in men",
                raw_text="Creatinine > 1.5 mg/dL in men",
                confidence=0.94,
            ),
        ],
        parsing_confidence=0.95,
        total_rules_extracted=3,
        model_used="gpt-4o-mini",
        reasoning_steps=None,
    )
    mock_parse.return_value = mock_response
    
    nct_id = "NCT05999006"
    raw_text = """
    Inclusion Criteria:
    - Hemoglobin A1c (HbA1c) ≥ 7.0% and ≤ 10.0%
    - eGFR ≥ 60 mL/min/1.73m²
    
    Exclusion Criteria:
    - Creatinine > 1.5 mg/dL in men
    """

    payload = {"raw_text": raw_text}
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["total_rules_extracted"] == 3
    
    # Check that rules have operators and values
    hba1c_rule = data["inclusion_criteria"][0]
    assert hba1c_rule["operator"] == "between"
    assert hba1c_rule["value"] == "7.0-10.0"
    assert hba1c_rule["unit"] == "%"


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_medical_coding_mocked(mock_parse, client_with_mocked_llm):
    """Test parsing with medical conditions and ICD-10 codes (mocked)."""
    mock_response = ParsedCriteriaResponse(
        nct_id="NCT05999007",
        parsing_timestamp=datetime(2024, 1, 1, 12, 0, 0),
        inclusion_criteria=[
            InclusionCriteriaRule(
                rule_id="inc_001",
                type="condition",
                identifier=["type 2 diabetes"],
                field="diagnosis",
                operator="==",
                value="Type 2 Diabetes Mellitus",
                unit=None,
                description="Diagnosed with Type 2 Diabetes Mellitus",
                raw_text="Diagnosed with Type 2 Diabetes Mellitus",
                confidence=0.95,
                code_system="ICD-10",
                code="E11",
            ),
        ],
        exclusion_criteria=[
            ExclusionCriteriaRule(
                rule_id="exc_001",
                type="condition",
                identifier=["copd"],
                field="diagnosis",
                operator="==",
                value="COPD",
                unit=None,
                description="Chronic obstructive pulmonary disease (COPD)",
                raw_text="Chronic obstructive pulmonary disease (COPD)",
                confidence=0.93,
                code_system="ICD-10",
                code="J44",
            ),
        ],
        parsing_confidence=0.94,
        total_rules_extracted=2,
        model_used="gpt-4o-mini",
        reasoning_steps=None,
    )
    mock_parse.return_value = mock_response
    
    nct_id = "NCT05999007"
    raw_text = """
    Inclusion Criteria:
    - Diagnosed with Type 2 Diabetes Mellitus
    
    Exclusion Criteria:
    - Chronic obstructive pulmonary disease (COPD)
    """

    payload = {"raw_text": raw_text}
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )

    assert response.status_code in [200, 201]
    data = response.json()
    
    # Check medical coding
    diabetes_rule = data["inclusion_criteria"][0]
    assert diabetes_rule["code_system"] == "ICD-10"
    assert diabetes_rule["code"] == "E11"
    
    copd_rule = data["exclusion_criteria"][0]
    assert copd_rule["code_system"] == "ICD-10"
    assert copd_rule["code"] == "J44"


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_parse_criteria_missing_payload(client_with_mocked_llm):
    """Test parsing without payload."""
    nct_id = "NCT05999008"
    
    response = client_with_mocked_llm.post(f"/api/ms2/parse-criteria/{nct_id}")
    
    assert response.status_code == 422


def test_parse_criteria_invalid_json(client_with_mocked_llm):
    """Test parsing with malformed JSON."""
    nct_id = "NCT05999009"
    
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        data="not a json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_llm_error_mocked(mock_parse, client_with_mocked_llm):
    """Test handling of LLM API errors (mocked)."""
    # Simulate LLM error
    mock_parse.side_effect = RuntimeError("OpenAI API error")
    
    nct_id = "NCT05999010"
    payload = {"raw_text": "Age 18-65"}
    
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )
    
    # Should handle error gracefully
    assert response.status_code == 500


# ============================================================================
# Performance Tests
# ============================================================================

@patch("src.ms2.ms2_main.MS2Service.parse_criteria")
def test_parse_criteria_performance_mocked(mock_parse, client_with_mocked_llm, mock_llm_response):
    """Test response time with mocked LLM (should be fast)."""
    import time
    
    mock_parse.return_value = mock_llm_response
    
    nct_id = "NCT05999999"
    payload = {"raw_text": "Age 18-65\nType 2 Diabetes"}
    
    start_time = time.time()
    response = client_with_mocked_llm.post(
        f"/api/ms2/parse-criteria/{nct_id}",
        json=payload,
    )
    end_time = time.time()
    
    assert response.status_code in [200, 201]
    
    # Should be very fast with mocked responses (< 1 second)
    elapsed = end_time - start_time
    assert elapsed < 1.0, f"Request took {elapsed:.2f}s, expected < 1s with mocks"
    print(f"Response time: {elapsed:.3f}s")


# ============================================================================
# Unit Tests for MS2Service Methods
# ============================================================================

@pytest.mark.asyncio
async def test_ms2_service_parse_empty_text():
    """Test MS2Service.parse_criteria with empty text (no LLM call)."""
    with patch("src.ms2.ms2_main.instructor.from_openai"):
        from src.ms2.ms2_main import MS2Service
        
        service = MS2Service()
        
        # Test empty criteria (shouldn't call LLM)
        result = await service.parse_criteria(
            nct_id="NCT12345",
            raw_text="",
            include_reasoning=False,
        )
        
        assert result.nct_id == "NCT12345"
        assert len(result.inclusion_criteria) == 0
        assert len(result.exclusion_criteria) == 0
        assert result.total_rules_extracted == 0
        assert result.model_used == "none"
        assert result.parsing_confidence == 0.0


@pytest.mark.asyncio
async def test_medical_coding_service():
    """Test medical coding enrichment."""
    from src.ms2.ms2_main import MedicalCodingService
    
    service = MedicalCodingService()
    
    # Test ICD-10 code lookup
    rule_dict = {
        "rule_id": "inc_001",
        "type": "condition",
        "description": "Type 2 Diabetes",
        "raw_text": "Type 2 Diabetes",
    }
    
    enriched = await service.enrich_rule_with_codes(rule_dict)
    
    assert enriched["code_system"] == "ICD-10"
    assert enriched["code"] == "E11"


# ============================================================================
# Note About Real API Tests
# ============================================================================

# All tests above use mocked OpenAI API calls
# To run integration tests with real OpenAI API:
# 1. Ensure OPENAI_API_KEY is set in environment
# 2. Create separate test file: test_ms2_integration.py
# 3. Mark tests with @pytest.mark.integration
# 4. Run with: pytest -m integration

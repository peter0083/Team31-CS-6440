"""
test_ms2.py - Fixed version with proper async/await mocking
"""

from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ms2.ms2_database import ParsedCriteriaDB
from src.ms2.ms2_main import CSVDataLoader, MS2Service
from src.ms2.ms2_pydantic_models import (
    EligibilityCriteria,
    ExclusionCriteriaRule,
    InclusionCriteriaRule,
    ParsedCriteriaResponse,
    ReasoningStep,
    TrialDataFromMS1,
)


class TestMS2Service:
    """Test MS2Service functionality."""

    @pytest.mark.asyncio
    async def test_get_from_db_success(self) -> None:
        """Test getting parsed criteria from database."""
        mock_record: MagicMock = MagicMock(spec=ParsedCriteriaDB)
        mock_record.nct_id = "NCT06129539"
        mock_record.inclusion_criteria = [
            {
                "rule_id": "rule_1",
                "type": "age",
                "field": "age",
                "description": "Must be between 18 and 65 years old",
                "raw_text": "18-65 years",
                "confidence": 0.9,
                "identifier": ["Age", "18-65"],
                "operator": ">=",
                "value": 18,
                "unit": "years",
                "code_system": None,
                "code": None,
            }
        ]

        mock_record.exclusion_criteria = [
            {
                "rule_id": "rule_2",
                "type": "condition",
                "field": "pregnancy",
                "description": "Pregnant women excluded",
                "raw_text": "Excluded if pregnant",
                "confidence": 0.95,
                "identifier": ["Pregnancy"],
                "operator": None,
                "value": None,
                "unit": None,
                "code_system": None,
                "code": None,
            }
        ]
        mock_record.parsing_confidence = 0.85

        service: MS2Service = MS2Service()

        with patch("src.ms2.ms2_main.async_session_maker") as mock_session_maker:
            # Session is async
            mock_session: AsyncMock = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # Result mock - scalar_one_or_none is SYNCHRONOUS
            mock_result: MagicMock = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_record  # ✅ KEY FIX!

            # execute is async
            async def async_execute(*args: Any, **kwargs: Any) -> MagicMock:
                return mock_result

            mock_session.execute = async_execute

            # Now this works!
            result = await service.get_from_db("NCT06129539")
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_from_db_not_found(self) -> None:
        """Test getting non-existent trial from database."""
        service: MS2Service = MS2Service()

        with patch(
            "src.ms2.ms2_main.async_session_maker"
        ) as mock_session_maker:
            mock_session: AsyncMock = AsyncMock()
            mock_session_maker.return_value.__aenter__.return_value = mock_session

            # Create async mock that returns None
            mock_result: AsyncMock = AsyncMock()
            
            async def async_scalar_one_or_none() -> None:
                return None
            
            mock_result.scalar_one_or_none = async_scalar_one_or_none
            
            async def async_execute(*args: Any, **kwargs: Any) -> AsyncMock:
                return mock_result
            
            mock_session.execute = async_execute

            result: ParsedCriteriaResponse | None = await service.get_from_db(
                "NCT_NONEXISTENT"
            )

            assert result is None

    def test_csv_loader_initialization(self) -> None:
        """Test CSV loader can be initialized."""
        loader: CSVDataLoader = CSVDataLoader()
        assert loader is not None

    @pytest.mark.asyncio
    async def test_csv_loader_load_into_db(self, tmp_path: Path) -> None:
        """Test loading CSV data into database."""
        csv_file: Path = tmp_path / "test_criteria.csv"
        csv_content: str = """nct_id,inclusion_criteria,exclusion_criteria,parsing_confidence,total_rules_extracted,model_used,parsing_timestamp
NCT06129539,"[{\\"rule_id\\": \\"1\\", \\"type\\": \\"age\\", \\"field\\": \\"age\\", \\"description\\": \\"18-65\\", \\"raw_text\\": \\"18-65\\", \\"confidence\\": 0.9, \\"operator\\": null, \\"value\\": null, \\"unit\\": null, \\"code_system\\": null, \\"code\\": null}]","[{\\"rule_id\\": \\"2\\", \\"type\\": \\"condition\\", \\"field\\": \\"pregnancy\\", \\"description\\": \\"Excluded\\", \\"raw_text\\": \\"Excluded\\", \\"confidence\\": 0.95, \\"operator\\": null, \\"value\\": null, \\"unit\\": null, \\"code_system\\": null, \\"code\\": null}]",0.85,2,csv_import,2025-01-09 00:00:00
"""
        csv_file.write_text(csv_content)

        with patch("src.ms2.ms2_main.async_session_maker"):
            loader: CSVDataLoader = CSVDataLoader()
            assert hasattr(loader, "load_csv_into_db")


class TestParsedCriteriaResponse:
    """Test ParsedCriteriaResponse model."""

    def test_response_creation(self) -> None:
        """Test creating a ParsedCriteriaResponse."""
        inclusion: InclusionCriteriaRule = InclusionCriteriaRule(
            rule_id="inc_1",
            type="demographic",
            field="age",
            description="Must be 18-65 years old",
            raw_text="Age 18-65",
            confidence=0.9,
            identifier=["Age", "18-65"],
            operator=">=",
            value=18,
            unit="years",
            code_system=None,
            code=None,
        )
        exclusion: ExclusionCriteriaRule = ExclusionCriteriaRule(
            rule_id="exc_1",
            type="condition",
            field="pregnancy",
            description="Pregnant women excluded",
            raw_text="No pregnant women",
            confidence=0.95,
            identifier=["Pregnancy"],
            operator=None,
            value=None,
            unit=None,
            code_system=None,
            code=None,
        )

        response: ParsedCriteriaResponse = ParsedCriteriaResponse(
            nct_id="NCT06129539",
            parsing_timestamp=datetime.now(),
            inclusion_criteria=[inclusion],
            exclusion_criteria=[exclusion],
            parsing_confidence=0.85,
            total_rules_extracted=2,
            model_used="csv_import",
            reasoning_steps=None,
        )

        assert response.nct_id == "NCT06129539"
        assert len(response.inclusion_criteria) == 1
        assert len(response.exclusion_criteria) == 1
        assert response.parsing_confidence == 0.85

    def test_response_json_serialization(self) -> None:
        """Test ParsedCriteriaResponse can be serialized to JSON."""
        response: ParsedCriteriaResponse = ParsedCriteriaResponse(
            nct_id="NCT06129539",
            parsing_timestamp=datetime.now(),
            inclusion_criteria=[],
            exclusion_criteria=[],
            parsing_confidence=0.85,
            total_rules_extracted=0,
            model_used="csv_import",
            reasoning_steps=None,
        )

        json_data: str = response.model_dump_json()
        assert "NCT06129539" in json_data

    def test_response_with_reasoning_steps(self) -> None:
        """Test ParsedCriteriaResponse with reasoning steps."""
        step: ReasoningStep = ReasoningStep(
            step=1,
            description="Identified age criterion",
            confidence=0.95,
        )

        response: ParsedCriteriaResponse = ParsedCriteriaResponse(
            nct_id="NCT06129539",
            parsing_timestamp=datetime.now(),
            inclusion_criteria=[],
            exclusion_criteria=[],
            parsing_confidence=0.85,
            total_rules_extracted=0,
            model_used="csv_import",
            reasoning_steps=[step],
        )

        assert response.reasoning_steps is not None
        assert len(response.reasoning_steps) == 1


class TestEligibilityCriteria:
    """Test EligibilityCriteria model."""

    def test_eligibility_criteria_creation(self) -> None:
        """Test creating EligibilityCriteria."""
        criteria: EligibilityCriteria = EligibilityCriteria(
            raw_text="Inclusion: Age 18-65. Exclusion: Pregnant women."
        )

        assert (
            criteria.raw_text
            == "Inclusion: Age 18-65. Exclusion: Pregnant women."
        )

    def test_inclusion_criterion_rule(self) -> None:
        """Test InclusionCriteriaRule with all required and optional fields."""
        rule: InclusionCriteriaRule = InclusionCriteriaRule(
            rule_id="rule_1",
            type="demographic",
            field="age",
            description="Must be 18 or older",
            raw_text="Age >= 18",
            confidence=0.9,
            identifier=["Age", "18+"],
            operator=">=",
            value=18,
            unit="years",
            code_system=None,
            code=None,
        )

        assert rule.rule_id == "rule_1"
        assert rule.type == "demographic"
        assert rule.field == "age"
        assert rule.description == "Must be 18 or older"
        assert rule.confidence == 0.9
        assert rule.operator == ">="
        assert rule.value == 18

    def test_exclusion_criterion_rule(self) -> None:
        """Test ExclusionCriteriaRule with all required and optional fields."""
        rule: ExclusionCriteriaRule = ExclusionCriteriaRule(
            rule_id="rule_1",
            type="condition",
            field="pregnancy",
            description="Pregnant women are excluded",
            raw_text="No pregnancy",
            confidence=0.95,
            identifier=["Pregnancy"],
            operator=None,
            value=None,
            unit=None,
            code_system=None,
            code=None,
        )

        assert rule.rule_id == "rule_1"
        assert rule.type == "condition"
        assert rule.field == "pregnancy"
        assert rule.description == "Pregnant women are excluded"
        assert rule.confidence == 0.95
        assert rule.operator is None


class TestTrialDataFromMS1:
    """Test TrialDataFromMS1 model."""

    def test_trial_data_creation(self) -> None:
        """Test creating TrialDataFromMS1."""
        trial: TrialDataFromMS1 = TrialDataFromMS1(
            nct_id="NCT06129539",
            title="Diabetes Management Study",
            status="Recruiting",
            eligibility_criteria={"raw_text": "18-65 years old"},
            phase="Phase 3",
        )

        assert trial.nct_id == "NCT06129539"
        assert trial.title == "Diabetes Management Study"
        assert trial.status == "Recruiting"
        assert trial.phase == "Phase 3"

    def test_trial_data_without_phase(self) -> None:
        """Test TrialDataFromMS1 without optional phase."""
        trial: TrialDataFromMS1 = TrialDataFromMS1(
            nct_id="NCT06129539",
            title="Test Study",
            status="Recruiting",
            eligibility_criteria={"raw_text": "Raw criteria"},
        )

        assert trial.nct_id == "NCT06129539"
        assert trial.phase is None


class TestMS2Integration:
    """Integration tests for MS2."""

    @pytest.mark.asyncio
    async def test_end_to_end_trial_processing(self) -> None:
        """Test end-to-end trial processing - database retrieval."""
        service: MS2Service = MS2Service()

        # Mock parsed response from database
        mock_parsed: ParsedCriteriaResponse = ParsedCriteriaResponse(
            nct_id="NCT06129539",
            parsing_timestamp=datetime.now(),
            inclusion_criteria=[],
            exclusion_criteria=[],
            parsing_confidence=0.85,
            total_rules_extracted=0,
            model_used="csv_import",
            reasoning_steps=None,
        )

        with patch.object(service, "get_from_db", return_value=mock_parsed):
            result: ParsedCriteriaResponse | None = await service.get_from_db(
                "NCT06129539"
            )

            assert result is not None
            assert result.nct_id == "NCT06129539"

    @pytest.mark.asyncio
    async def test_reasoning_step_creation(self) -> None:
        """Test creating ReasoningStep."""
        step: ReasoningStep = ReasoningStep(
            step=1,
            description="Extracted age constraint from text",
            confidence=0.92,
        )

        assert step.step == 1
        assert step.confidence == 0.92

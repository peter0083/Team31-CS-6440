"""MS2 Microservice: clinical trial criteria parser with LLM.
Configuration: gpt-4o-mini only + PostgreSQL
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

import httpx

# instructor library does not provide type stubs (.pyi files) or py.typed marker,
# so mypy cannot verify its types. Skip type checking for this import.
import instructor  # type: ignore[import-untyped]
from fastapi import FastAPI
from openai import AsyncOpenAI
from sqlalchemy import select

from src.ms2.ms2_config import settings
from src.ms2.ms2_database import ParsedCriteriaDB, async_session_maker
from src.ms2.ms2_pydantic_models import (
    ExclusionCriteriaRule,
    InclusionCriteriaRule,
    ParsedCriteriaResponse,
    ReasoningStep,
    TrialDataFromMS1,
)


class MedicalCodingService:
    """Service for mapping medical terms to ICD-10 codes."""

    def __init__(self) -> None:
        self.icd10_cache = {
            "type 2 diabetes": "E11",
            "type 2 diabetes mellitus": "E11",
            "diabetes mellitus type 2": "E11",
            "type 1 diabetes": "E10",
            "hypertension": "I10",
            "essential hypertension": "I10",
            "breast cancer": "C50",
            "malignant neoplasm of breast": "C50",
            "copd": "J44",
            "chronic obstructive pulmonary disease": "J44",
            "asthma": "J45",
            "heart failure": "I50",
            "chronic kidney disease": "N18",
            "ckd": "N18",
            "depression": "F32",
            "rheumatoid arthritis": "M06",
        }

    async def get_icd10_code(self, condition: str) -> Optional[str]:
        """Map condition to ICD-10 code."""
        normalized = condition.lower().strip()
        code = self.icd10_cache.get(normalized)
        return code if isinstance(code, str) else None

    async def enrich_rule_with_codes(self, rule: dict) -> dict:
        """Enrich a rule with medical codes."""
        if rule.get("type") == "condition" and not rule.get("code"):
            condition = rule.get("description") or rule.get("field")
            if condition:
                code = await self.get_icd10_code(condition)
                if code:
                    rule["code_system"] = "ICD-10"
                    rule["code"] = code
        return rule


class MS1Client:
    """Client for fetching data from MS1."""

    def __init__(self) -> None:
        self.base_url = settings.MS1_URL
        self.timeout = settings.MS1_TIMEOUT

    async def get_trial(self, nct_id: str) -> Optional[TrialDataFromMS1]:
        """Fetch trial data from MS1."""
        url = f"{self.base_url}/api/ms1/trials/{nct_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                return TrialDataFromMS1(**data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            raise


class MS2Service:
    """LLM-powered clinical trial criteria parser.
    Configuration: gpt-4o-mini only + PostgreSQL
    """

    def __init__(self) -> None:
        self.client = instructor.from_openai(
            AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.LLM_TIMEOUT,
            )
        )
        self.medical_coding = MedicalCodingService()
        self.ms1_client = MS1Client()

        self.system_prompt = """You are an expert medical NLP system specializing in clinical trial eligibility criteria parsing.

        Your task: Parse free-text eligibility criteria into structured, machine-readable rules.

        RULE TYPES:
        - demographic: age, gender, race, ethnicity, BMI
        - condition: diseases, diagnoses (use ICD-10 codes when possible)
        - lab_value: laboratory tests (HbA1c, creatinine, etc.)
        - medication: drug requirements or restrictions
        - procedure: surgical/medical procedures
        - behavioral: smoking, alcohol use, lifestyle factors

        OPERATORS: between, >=, <=, >, <, =

        IDENTIFIER FIELD:
        - Generate an array of 1-3 keywords that identify what this rule is about
        - Examples:
          * Age criterion → ["age"]
          * HbA1c test → ["test", "HbA1c"]
          * Diabetes diagnosis → ["diagnosis", "diabetes"]
          * Pregnancy status → ["pregnancy_status"]
        - Use lowercase, underscore-separated keywords
        - Be specific and meaningful

        MEDICAL CODING:
        - Map conditions to ICD-10 codes (e.g., "Type 2 diabetes" → E11)
        - Include standard units for lab values
        - Preserve exact terminology from raw text

        PARSING RULES:
        1. Each criterion = ONE atomic rule
        2. Split "AND" conditions into separate rules
        3. Generate sequential rule IDs: inc_001, inc_002, exc_001, etc.
        4. Preserve EXACT raw text (no paraphrasing)
        5. Always include the identifier array for each rule

        NEGATION HANDLING:
        - "No history of X" → exclusion criterion
        - "Absence of X" → exclusion criterion

        CONFIDENCE SCORING (0.0-1.0):
        - 0.9-1.0: Clear, unambiguous
        - 0.7-0.9: Minor ambiguity
        - 0.5-0.7: Significant ambiguity
        - <0.5: Highly ambiguous
        """

    async def get_from_db(self, nct_id: str) -> Optional[ParsedCriteriaResponse]:
        """Get parsed criteria from database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ParsedCriteriaDB).where(ParsedCriteriaDB.nct_id == nct_id)
                )
                db_record = result.scalar_one_or_none()

                if db_record:
                    # Assert that these are lists, not Column objects
                    inclusion_data: list[Any] = db_record.inclusion_criteria or []  # type: ignore[assignment]
                    exclusion_data: list[Any] = db_record.exclusion_criteria or []  # type: ignore[assignment]
                    reasoning_data: list[Any] = db_record.reasoning_steps or []  # type: ignore[assignment]

                    return ParsedCriteriaResponse(
                        nct_id=str(db_record.nct_id),
                        parsing_timestamp=db_record.parsing_timestamp,  # type: ignore[arg-type]
                        inclusion_criteria=[
                            InclusionCriteriaRule(**r) for r in inclusion_data  # type: ignore[union-attr]
                        ],
                        exclusion_criteria=[
                            ExclusionCriteriaRule(**r) for r in exclusion_data  # type: ignore[union-attr]
                        ],
                        parsing_confidence=float(db_record.parsing_confidence),
                        total_rules_extracted=int(db_record.total_rules_extracted),
                        model_used=str(db_record.model_used),
                        reasoning_steps=[
                            ReasoningStep(**s) for s in reasoning_data  # type: ignore[union-attr]
                        ] if reasoning_data else None,
                    )

                return None
        except Exception as e:
            raise RuntimeError(f"Failed to load settings: {e}") from e

    async def save_to_db(
            self,
            parsed: ParsedCriteriaResponse,
            trial_data: TrialDataFromMS1
    ) -> None:
        """Save parsed criteria to database."""
        try:
            async with async_session_maker() as session:
                db_obj = ParsedCriteriaDB(
                    nct_id=parsed.nct_id,
                    parsing_timestamp=parsed.parsing_timestamp,
                    inclusion_criteria=[r.model_dump() for r in parsed.inclusion_criteria],
                    exclusion_criteria=[r.model_dump() for r in parsed.exclusion_criteria],
                    parsing_confidence=parsed.parsing_confidence,
                    total_rules_extracted=parsed.total_rules_extracted,
                    model_used=parsed.model_used,
                    reasoning_steps=[
                        s.model_dump() for s in parsed.reasoning_steps
                    ] if parsed.reasoning_steps else None,
                    raw_input=trial_data.model_dump(),
                )

                # Merge (upsert) to handle duplicates
                await session.merge(db_obj)
                await session.commit()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to save to DB: {e}")

    async def parse_criteria(
            self,
            nct_id: str,
            raw_text: str,
            include_reasoning: bool = False,
    ) -> ParsedCriteriaResponse:
        """
        Parse clinical trial eligibility criteria using LLM.

        Args:
            nct_id: NCT identifier
            raw_text: Raw eligibility criteria text
            include_reasoning: Include chain-of-thought reasoning

        Returns:
            ParsedCriteriaResponse with structured rules

        Raises:
            Exception: If parsing fails after all retries
        """
        if not raw_text or raw_text.strip() == "":
            return ParsedCriteriaResponse(
                nct_id=nct_id,
                parsing_timestamp=datetime.now(),
                inclusion_criteria=[],
                exclusion_criteria=[],
                parsing_confidence=0.0,
                total_rules_extracted=0,
                model_used="none",
                reasoning_steps=None,
            )

        # Build prompt
        user_prompt = f"""NCT ID: {nct_id}
        
        ELIGIBILITY CRITERIA TO PARSE:
        {raw_text}
        
        Generate sequential rule IDs starting from inc_001 for inclusion and exc_001 for exclusion.
        Parse ALL criteria comprehensively. Return complete structured output."""

        # Parse with retries
        for attempt in range(settings.LLM_MAX_RETRIES):
            try:
                result = await self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    response_model=ParsedCriteriaResponse,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                )

                # Add type assertion for mypy
                assert isinstance(result, ParsedCriteriaResponse)

                # Post-process: enrich with medical codes
                if settings.ENABLE_MEDICAL_CODING:
                    inclusion_enriched = []
                    for rule in result.inclusion_criteria:
                        rule_dict = rule.model_dump()
                        enriched = await self.medical_coding.enrich_rule_with_codes(
                            rule_dict
                        )
                        inclusion_enriched.append(InclusionCriteriaRule(**enriched))
                    result.inclusion_criteria = inclusion_enriched

                    exclusion_enriched: list[ExclusionCriteriaRule] = []
                    for rule in result.exclusion_criteria:  # type: ignore[assignment]
                        rule_dict = rule.model_dump()
                        enriched = await self.medical_coding.enrich_rule_with_codes(rule_dict)
                        exclusion_enriched.append(ExclusionCriteriaRule(**enriched))
                    result.exclusion_criteria = exclusion_enriched

                # Set metadata
                result.parsing_timestamp = datetime.now()
                result.total_rules_extracted = len(result.inclusion_criteria) + len(
                    result.exclusion_criteria
                )
                result.model_used = settings.OPENAI_MODEL

                return result

            except Exception:
                if attempt == settings.LLM_MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # This line is technically unreachable, but it is kept here for type safety
        raise RuntimeError(f"Failed to parse criteria for {nct_id} after all retries")

    async def get_trial_from_ms1_and_parse(
            self,
            nct_id: str,
            include_reasoning: bool = False,
            force_refresh: bool = False,
    ) -> ParsedCriteriaResponse:
        """
        Fetch trial from MS1 and parse criteria.
        Uses database cache unless force_refresh is True.

        Args:
            nct_id: NCT identifier
            include_reasoning: Include reasoning steps
            force_refresh: Skip database cache and reparse

        Returns:
            ParsedCriteriaResponse
        """
        # Check database cache first (unless force_refresh)
        if not force_refresh:
            cached = await self.get_from_db(nct_id)
            if cached:
                return cached

        # Fetch from MS1
        trial_data = await self.ms1_client.get_trial(nct_id)
        if not trial_data:
            raise ValueError(f"Trial {nct_id} not found in MS1")

        # Extract raw criteria text
        raw_text = trial_data.eligibility_criteria.get("raw_text", "")

        # Parse with LLM
        parsed = await self.parse_criteria(
            nct_id=nct_id,
            raw_text=raw_text,
            include_reasoning=include_reasoning,
        )

        # Save to database (async, don't wait)
        await self.save_to_db(parsed, trial_data)

        return parsed


# FastAPI app initialization
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    from src.ms2.ms2_routes import lifespan, router

    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.VERSION,
        description="Clinical Trial Eligibility Criteria Parser with LLM",
        lifespan=lifespan,
    )

    # Include MS2 routes
    app.include_router(router, prefix="/api/ms2")

    return app

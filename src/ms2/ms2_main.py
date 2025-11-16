import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import instructor  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

logger = logging.getLogger(__name__)


class CSVDataLoader:
    @staticmethod
    async def load_csv_into_db(csv_path: str) -> int:
        csv_file = Path(csv_path)

        if not csv_file.exists():
            logger.warning(f"⚠️ CSV file not found: {csv_path}")
            return 0

        try:
            # Step 1: Read CSV and group rules by nct_id
            trials_data: dict[str, Any] = {}

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    nct_id = row['nct_id'].strip()
                    rule_type_value = row['rule_type'].strip()  # 'inclusion' or 'exclusion'

                    # Initialize trial entry if not exists
                    if nct_id not in trials_data:
                        trials_data[nct_id] = {
                            'nct_id': nct_id,
                            'parsing_timestamp': datetime.now(),
                            'inclusion_criteria': [],
                            'exclusion_criteria': [],
                            'parsing_confidence': 0.85,  # Default
                            'total_rules_extracted': 0,
                            'model_used': 'csv_import',
                            'source': 'csv_import',
                            'raw_input': {},
                            'reasoning_steps': None,
                        }

                    # Parse identifier JSON
                    try:
                        identifier = json.loads(row['identifier'].strip())
                    except (json.JSONDecodeError, KeyError, ValueError):
                        identifier = [row.get('type', 'unknown').strip()]

                    # Build rule object
                    rule = {
                        'rule_id': row['rule_id'].strip(),
                        'type': row['type'].strip(),
                        'identifier': identifier,
                        'field': row['field'].strip(),
                        'operator': row['operator'].strip() if row['operator'].strip() else None,
                        'value': row['value'].strip() if row['value'].strip() else None,
                        'unit': row['unit'].strip() if row['unit'].strip() else None,
                        'raw_text': row['raw_text'].strip(),
                        'confidence': float(row['confidence']),
                        'description': row['raw_text'].strip()[:100],
                        'code_system': None,
                        'code': None,
                    }

                    # Add rule to appropriate list
                    if rule_type_value == 'inclusion':
                        trials_data[nct_id]['inclusion_criteria'].append(rule)
                    elif rule_type_value == 'exclusion':
                        trials_data[nct_id]['exclusion_criteria'].append(rule)

            # Step 2: Calculate total rules and save to database
            async with async_session_maker() as session:
                saved_count = 0

                for trial_data in trials_data.values():
                    # Calculate totals
                    trial_data['total_rules_extracted'] = (
                        len(trial_data['inclusion_criteria'])
                        + len(trial_data['exclusion_criteria'])
                    )

                    # Create database record
                    try:
                        db_record = ParsedCriteriaDB(
                            nct_id=trial_data['nct_id'],
                            parsing_timestamp=trial_data['parsing_timestamp'],
                            inclusion_criteria=trial_data['inclusion_criteria'],
                            exclusion_criteria=trial_data['exclusion_criteria'],
                            parsing_confidence=trial_data['parsing_confidence'],
                            total_rules_extracted=trial_data['total_rules_extracted'],
                            model_used=trial_data['model_used'],
                            source=trial_data['source'],
                            raw_input=trial_data['raw_input'],
                            reasoning_steps=trial_data['reasoning_steps'],
                        )

                        # Upsert (merge) - replaces if exists
                        await session.merge(db_record)
                        saved_count += 1

                    except Exception as e:
                        logger.error(
                            f"❌ Failed to save {trial_data['nct_id']}: {e}"
                        )
                        continue

                # Commit all changes
                await session.commit()

            logger.info(
                f"✅ Successfully ingested {saved_count} trials from CSV: {csv_path}"
            )
            logger.info(
                f"   Total rules loaded: {sum(t['total_rules_extracted'] for t in trials_data.values())}"
            )

            return saved_count

        except Exception as e:
            logger.error(f"❌ Failed to load CSV: {e}", exc_info=True)
            return 0


class MedicalCodingService:
    """map medical terms to ICD-10 codes."""

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
            "unspecified dementia": "F03",
            "Malignant (primary) neoplasm, unspecified, (cancer)": "C80.1",
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


class MS2Service:
    """call LLM to parse"""

    def __init__(self) -> None:
        self.has_openai_key = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())

        if self.has_openai_key:
            self.client = instructor.from_openai(
                AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=settings.LLM_TIMEOUT,
                )
            )
        else:
            self.client = None
            logger.warning("⚠️ OPENAI_API_KEY not configured. Using database-only mode.")

        self.medical_coding = MedicalCodingService()

        self.system_prompt = """You are an expert medical NLP system specializing in clinical trial eligibility criteria parsing.

Your task: Parse free-text eligibility criteria into structured, machine-readable rules."""

    async def get_from_db(self, nct_id: str) -> ParsedCriteriaResponse | None:
        """Get parsed criteria from database."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(
                    select(ParsedCriteriaDB).where(
                        ParsedCriteriaDB.nct_id == nct_id
                    )
                )

                db_record = result.scalar_one_or_none()

                if db_record:
                    inclusion_data: list[Any] = (
                        list(db_record.inclusion_criteria)
                        if db_record.inclusion_criteria
                        else []
                    )
                    exclusion_data: list[Any] = (
                        list(db_record.exclusion_criteria)
                        if db_record.exclusion_criteria
                        else []
                    )
                    reasoning_data: list[Any] = (
                        list(db_record.reasoning_steps)
                        if db_record.reasoning_steps
                        else []
                    )

                    return ParsedCriteriaResponse(
                        nct_id=str(db_record.nct_id),
                        parsing_timestamp=(
                            db_record.parsing_timestamp
                            if isinstance(db_record.parsing_timestamp, datetime)
                            else datetime.now()
                        ),
                        inclusion_criteria=[
                            InclusionCriteriaRule(**r) for r in inclusion_data
                        ],
                        exclusion_criteria=[
                            ExclusionCriteriaRule(**r) for r in exclusion_data
                        ],
                        parsing_confidence=float(db_record.parsing_confidence),
                        total_rules_extracted=int(db_record.total_rules_extracted),
                        model_used=str(db_record.model_used),
                        reasoning_steps=(
                            [ReasoningStep(**s) for s in reasoning_data]
                            if reasoning_data
                            else None
                        ),
                    )

                return None
        except Exception as e:
            logger.error(f"❌ Database lookup failed: {e}", exc_info=True)
            return None

    async def save_to_db(
        self,
        parsed: ParsedCriteriaResponse,
        trial_data: TrialDataFromMS1,
        source: str = "openai",
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
                    reasoning_steps=(
                        [s.model_dump() for s in parsed.reasoning_steps]
                        if parsed.reasoning_steps
                        else None
                    ),
                    raw_input=trial_data.model_dump(),
                    source=source,
                )

                await session.merge(db_obj)
                await session.commit()
        except Exception as e:
            logger.error(f"❌ Failed to save to DB: {e}", exc_info=True)

    async def process_trial(
        self,
        nct_id: str,
        trial_data: TrialDataFromMS1,
    ) -> ParsedCriteriaResponse:
        logger.info(f"🔍 Checking database for {nct_id}...")
        cached = await self.get_from_db(nct_id)

        if cached:
            logger.info(f"✅ Found {nct_id} in database (source: {cached.model_used})")
            return cached

        logger.warning(f"⚠️ {nct_id} not in database and no OpenAI key configured")
        raise ValueError(
            f"❌ Trial {nct_id} not found in database. "
            "No OpenAI API key configured for real-time parsing."
        )


def create_app() -> FastAPI:
    """Create FastAPI app"""
    from src.ms2.ms2_routes import lifespan, router

    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.VERSION,
        description="Clinical Trial Eligibility Criteria Parser",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/ms2")

    return app


app = create_app()

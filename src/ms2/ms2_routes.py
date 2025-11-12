"""MS2 API routes - Clinical Trial Criteria Parser

Receives trial data from MS1, checks database first, then parses with OpenAI if needed.

Ingests CSV mock data on startup.

"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from sqlalchemy import select

from src.ms2.ms2_config import settings
from src.ms2.ms2_database import (
    ParsedCriteriaDB,
    async_session_maker,
    check_db_connection,
    close_db,
    init_db,
)
from src.ms2.ms2_main import CSVDataLoader, MS2Service
from src.ms2.ms2_pydantic_models import (
    ErrorResponse,
    HealthResponse,
    ParsedCriteriaResponse,
)

logger = logging.getLogger(__name__)

# Cache for received and parsed trials
received_trials: list[dict[str, Any]] = []
parsed_cache: dict[str, Any] = {}


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup on startup/shutdown."""
    # Startup
    print(f"\n{'='*60}")
    print(f"🚀 Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    print(f"{'='*60}\n")

    # Initialize database
    print("📊 Initializing database...")
    await init_db()
    print("✅ Database tables created")

    # Load CSV data if present
    print("\n📥 Checking for CSV mock data...")
    csv_paths = [
        "parsed_eligibility_criteria.csv",
        "data/ms2/parsed_eligibility_criteria.csv",
        "src/ms2/parsed_eligibility_criteria.csv",
    ]

    csv_loaded = False
    for csv_path in csv_paths:
        if Path(csv_path).exists():
            print(f" Found: {csv_path}")
            records = await CSVDataLoader.load_csv_into_db(csv_path)
            if records > 0:
                print(f"✅ Loaded {records} trials from CSV into PostgreSQL")
                csv_loaded = True
                break

    if not csv_loaded:
        print("⚠️ No CSV mock data found (optional)")

    # Check OpenAI configuration
    print("\n🔑 Checking OpenAI configuration...")
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        print("✅ OpenAI API key configured")
        print(f" Model: {settings.OPENAI_MODEL}")
    else:
        print("⚠️ OPENAI_API_KEY not configured")
        print(" Will use database-only mode (CSV/import data only)")

    # Check database connection
    db_connected = await check_db_connection()
    if db_connected:
        print("\n✅ PostgreSQL database connected")
        # Count existing parsed criteria
        async with async_session_maker() as session:
            result = await session.execute(
                select(ParsedCriteriaDB).limit(1)
            )
            db_record = result.scalar_one_or_none()
            if db_record:
                print(" Database has pre-parsed trial data available")
    else:
        print("\n❌ PostgreSQL database NOT connected")
        print(" Warning: Database operations will fail")

    print(f"\n{'='*60}\n")

    yield

    # Shutdown
    print("\n🛑 Shutting down MS2...")
    await close_db()
    print("✅ Cleanup complete\n")


router = APIRouter()
service = MS2Service()
start_time = time.time()

# ════════════════════════════════════════════════════════════════════════════
# MS1-to-MS2 Integration Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.post(
    "/receive",
    tags=["MS1 Integration"],
    summary="Receive and process trial data from MS1",
)
async def receive_trials_from_ms1(request: Request) -> dict[str, Any]:
    """Receive clinical trial data from MS1 and process."""
    global received_trials, parsed_cache

    try:
        data = await request.json()

        if isinstance(data, dict):
            received_trials = [data]
        elif isinstance(data, list):
            received_trials = data
        else:
            raise ValueError("Expected dict or list of trials")

        count = len(received_trials)
        logger.info(f"📦 Received {count} trial(s) from MS1")

        # Process all trials
        processing_results: dict[str, Any] = {
            "total_trials": count,
            "processed": [],
            "failed": [],
            "parsed_criteria": {},
            "api_key_missing": False,
        }

        for trial in received_trials:
            nct_id = trial.get("nct_id", "UNKNOWN")
            try:
                logger.info(f"⏳ Processing {nct_id}...")
                trial_data = {
                    "nct_id": nct_id,
                    "title": trial.get("title", ""),
                    "eligibility_criteria": trial.get("eligibility_criteria", {}),
                    "status": trial.get("recruitment_status", ""),
                }

                from src.ms2.ms2_main import TrialDataFromMS1

                trial_obj = TrialDataFromMS1(**trial_data)
                parsed = await service.process_trial(nct_id, trial_obj)

                # Cache the result
                parsed_cache[nct_id] = parsed.model_dump()

                # Include parsed data in response
                processing_results["parsed_criteria"][nct_id] = parsed.model_dump()

                logger.info(f"✅ Successfully processed {nct_id}")
                processing_results["processed"].append(
                    {
                        "nct_id": nct_id,
                        "title": trial.get("title"),
                        "confidence": parsed.parsing_confidence,
                        "rules_extracted": parsed.total_rules_extracted,
                        "source": "database"
                        if parsed.model_used == "csv_import"
                        else "openai",
                    }
                )

            except ValueError as e:
                if "OPENAI_API_KEY" in str(e):
                    logger.warning(f"⚠️ {nct_id}: No API key available")
                    processing_results["api_key_missing"] = True
                    processing_results["failed"].append(
                        {
                            "nct_id": nct_id,
                            "error": str(e),
                            "type": "api_key_missing",
                        }
                    )
                else:
                    logger.warning(f"⚠️ {nct_id}: {e}")
                    processing_results["failed"].append(
                        {
                            "nct_id": nct_id,
                            "error": str(e),
                            "type": "validation_error",
                        }
                    )

            except Exception as e:
                logger.error(f"❌ Failed to process {nct_id}: {e}")
                processing_results["failed"].append(
                    {
                        "nct_id": nct_id,
                        "error": str(e),
                        "type": "processing_error",
                    }
                )

        logger.info(
            f"📊 Processing complete: {len(processing_results['processed'])} "
            f"processed, {len(processing_results['failed'])} failed"
        )

        if (
            processing_results["api_key_missing"]
            and len(processing_results["processed"]) == 0
        ):
            return {
                "status": "error",
                "count": count,
                "message": (
                    "❌ OpenAI API key not configured. "
                    "Trials not found in database and cannot be parsed. "
                    "Please set OPENAI_API_KEY environment variable."
                ),
                "processing_results": processing_results,
            }

        # Include parsed data in return
        return {
            "status": "received_and_processed",
            "count": count,
            "message": f"Successfully processed {len(processing_results['processed'])} trial(s)",
            "processing_results": processing_results,
            "parsed_criteria": processing_results["parsed_criteria"],
        }

    except ValueError as e:
        logger.error(f"❌ Invalid data format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data format: {str(e)}",
        )

    except Exception as e:
        logger.error(f"❌ Error receiving/processing data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to receive/process data: {str(e)}",
        )


# ════════════════════════════════════════════════════════════════════════════
# Trial Parsing Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.get(
    "/parsed-criteria/{nct_id}",
    response_model=ParsedCriteriaResponse,
    tags=["Trial Parsing"],
    summary="Get parsed criteria for a trial",
    responses={
        200: {"description": "Parsed criteria found"},
        404: {"model": ErrorResponse, "description": "Trial not found"},
        500: {"model": ErrorResponse, "description": "Parsing error"},
    },
)
async def get_parsed_criteria(nct_id: str) -> ParsedCriteriaResponse:
    """
    Get parsed eligibility criteria for a trial.

    Priority:
    1. Check in-memory cache
    2. Check PostgreSQL database
    3. Return error if not found

    Args:
        nct_id: NCT identifier (e.g., NCT06129539)

    Returns:
        ParsedCriteriaResponse with inclusion/exclusion criteria rules
    """
    # Check cache first
    if nct_id in parsed_cache:
        logger.info(f"📦 Returning cached parsed criteria for {nct_id}")
        return ParsedCriteriaResponse(**parsed_cache[nct_id])

    # Check database
    try:
        cached = await service.get_from_db(nct_id)
        if cached:
            logger.info(f"📦 Returning database parsed criteria for {nct_id}")
            parsed_cache[nct_id] = cached.model_dump()
            return cached

    except Exception as e:
        logger.warning(f"⚠️ Database lookup failed: {e}")

    logger.warning(f"⚠️ Trial {nct_id} not found")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Trial {nct_id} not found in database. Send it from MS1 first.",
    )


@router.get(
    "/all-parsed",
    tags=["Trial Parsing"],
    summary="Get all parsed criteria metadata",
)
async def get_all_parsed() -> dict[str, Any]:
    """Get metadata for all parsed criteria in cache and database."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(ParsedCriteriaDB))
            all_records = result.scalars().all()

            return {
                "total_parsed": len(all_records),
                "parsed_trials": {
                    record.nct_id: {
                        "inclusion_count": len(record.inclusion_criteria or []),
                        "exclusion_count": len(record.exclusion_criteria or []),
                        "confidence": record.parsing_confidence,
                        "model_used": record.model_used,
                        "source": record.source,
                    }
                    for record in all_records
                },
            }

    except Exception as e:
        logger.error(f"❌ Failed to retrieve all parsed: {e}")
        return {
            "total_parsed": 0,
            "parsed_trials": {},
            "error": str(e),
        }


@router.get(
    "/trials",
    tags=["Trial Parsing"],
    summary="List all available trial NCT IDs",
    response_description="List of NCT IDs available in the database",
)
async def list_all_trials() -> dict[str, Any]:
    """
    List all trial NCT IDs that have parsed criteria in the database.

    Equivalent to: SELECT nct_id FROM parsed_criteria_db ORDER BY nct_id;

    Returns:
        Dictionary with list of NCT IDs and count

    Example response:
        {
            "total_trials": 42,
            "nct_ids": ["NCT00598351", "NCT01234567", ...],
            "database": "parsed_criteria_db"
        }
    """
    try:
        async with async_session_maker() as session:
            # Query all NCT IDs from database
            result = await session.execute(
                select(ParsedCriteriaDB.nct_id).order_by(ParsedCriteriaDB.nct_id)
            )

            nct_ids = [row[0] for row in result.all()]

            logger.info(f"📋 Retrieved {len(nct_ids)} trial NCT IDs from database")

            return {
                "total_trials": len(nct_ids),
                "nct_ids": nct_ids,
                "database": "parsed_criteria_db",
                "status": "success",
            }

    except Exception as e:
        logger.error(f"❌ Failed to list trials: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trial list: {str(e)}",
        )


@router.get(
    "/trials/summary",
    tags=["Trial Parsing"],
    summary="List trials with summary information",
)
async def list_trials_with_summary() -> dict[str, Any]:
    """
    List all trials with summary information (NCT ID, rule counts, confidence).

    Returns:
        Dictionary with detailed trial information
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(ParsedCriteriaDB).order_by(ParsedCriteriaDB.nct_id)
            )

            all_records = result.scalars().all()

            trials_summary = [
                {
                    "nct_id": record.nct_id,
                    "total_rules": record.total_rules_extracted,
                    "inclusion_count": len(record.inclusion_criteria or []),
                    "exclusion_count": len(record.exclusion_criteria or []),
                    "confidence": record.parsing_confidence,
                    "model": record.model_used,
                    "parsed_at": record.parsing_timestamp.isoformat()
                    if record.parsing_timestamp
                    else None,
                }
                for record in all_records
            ]

            return {
                "total_trials": len(trials_summary),
                "trials": trials_summary,
                "status": "success",
            }

    except Exception as e:
        logger.error(f"❌ Failed to list trials with summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trial summary: {str(e)}",
        )


# ════════════════════════════════════════════════════════════════════════════
# Health & Status Endpoints
# ════════════════════════════════════════════════════════════════════════════


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    db_connected = await check_db_connection()
    openai_status = "configured" if service.has_openai_key else "not_configured"

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        llm_provider=f"openai ({openai_status})",
        database_connected=db_connected,
        redis_connected=False,
        uptime_seconds=time.time() - start_time,
    )


@router.get(
    "/api/ms2/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health_check_alt() -> HealthResponse:
    """Alternative health check endpoint."""
    db_connected = await check_db_connection()
    openai_status = "configured" if service.has_openai_key else "not_configured"

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        llm_provider=f"openai ({openai_status})",
        database_connected=db_connected,
        redis_connected=False,
        uptime_seconds=time.time() - start_time,
    )


@router.get(
    "/",
    tags=["Info"],
)
async def root() -> dict[str, Any]:
    """Root endpoint - service information."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "openai_configured": service.has_openai_key,
        "model": settings.OPENAI_MODEL if service.has_openai_key else "N/A",
        "database_mode": "csv_import + openai"
        if service.has_openai_key
        else "csv_import_only",
        "docs": "/docs",
    }

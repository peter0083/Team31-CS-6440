"""API routes for MS2 microservice: clinical trial criteria parser.
Configuration: gpt-4o-mini only + PostgreSQL
"""

import time
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic_core._pydantic_core import ValidationError

from src.ms2.ms2_config import settings
from src.ms2.ms2_database import check_db_connection, close_db, init_db
from src.ms2.ms2_main import MS2Service
from src.ms2.ms2_pydantic_models import (
    EligibilityCriteria,
    ErrorResponse,
    HealthResponse,
    ParsedCriteriaResponse,
)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup on startup/shutdown."""
    # Startup
    print(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    await init_db()
    print("Database initialized")

    yield

    # Shutdown
    print("Shutting down...")
    await close_db()


router = APIRouter()
service = MS2Service()
start_time = time.time()


@router.get(
    "/parsed-criteria/{nct_id}",
    response_model=ParsedCriteriaResponse,
    tags=["MS2"],
    responses={
        404: {"model": ErrorResponse, "description": "Trial not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def get_parsed_criteria(
    nct_id: str,
    include_reasoning: bool = False,
    force_refresh: bool = False,
) -> ParsedCriteriaResponse:
    """
    Get parsed eligibility criteria for a clinical trial.

    Workflow:
    1. Check PostgreSQL database cache (unless force_refresh=True)
    2. If not cached, fetch from MS1
    3. Parse with gpt-4o-mini
    4. Save to database
    5. Return structured rules

    Args:
        nct_id: NCT identifier (e.g., NCT05123456)
        include_reasoning: Include chain-of-thought reasoning steps
        force_refresh: Skip database cache and reparse

    Returns:
        ParsedCriteriaResponse: Parsed criteria with structured rules

    Raises:
        HTTPException: If trial not found or parsing fails
    """
    try:
        result = await service.get_trial_from_ms1_and_parse(
            nct_id=nct_id,
            include_reasoning=include_reasoning,
            force_refresh=force_refresh,
        )
        return result
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing failed: {str(e)}",
        )


@router.post(
    "/parse-criteria/{nct_id}",
    response_model=ParsedCriteriaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["MS2"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
async def parse_criteria_on_demand(
    nct_id: str,
    criteria: EligibilityCriteria,
    include_reasoning: bool = False,
) -> ParsedCriteriaResponse:
    """
    Parse eligibility criteria on-demand (without MS1 dependency).

    Useful for testing or when you have criteria text already.
    Does NOT save to database.

    Args:
        nct_id: NCT identifier
        criteria: The eligibility criteria to parse
        include_reasoning: Include chain-of-thought reasoning

    Returns:
        ParsedCriteriaResponse: The parsed criteria response

    Raises:
        HTTPException: If parsing fails
    """
    try:
        result = await service.parse_criteria(
            nct_id=nct_id,
            raw_text=criteria.raw_text,
            include_reasoning=include_reasoning,
        )
        return result
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parsing failed: {str(e)}",
        )

@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["MS2"],
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and database connectivity.
    """
    db_connected = await check_db_connection()

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        service=settings.SERVICE_NAME,
        version=settings.VERSION,
        llm_provider="openai",
        database_connected=db_connected,
        redis_connected=False,  # Not using Redis yet
        uptime_seconds=time.time() - start_time,
    )


@router.get(
    "/",
    tags=["MS2"],
)
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "model": settings.OPENAI_MODEL,
        "docs": "/docs",
    }

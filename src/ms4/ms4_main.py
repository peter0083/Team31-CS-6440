# src/ms4/ms4_main.py
"""
MS4 Main Application - Updated Version

Updated MS4 main application that:
1. Waits for MS3 initialization
2. Loads all patient data into memory cache at startup
3. Uses cached data for trial matching (avoids redundant MS3 fetches)
4. Provides efficient batch trial-to-patient matching

Key improvement: Passes cached patient data to orchestrator for blazing-fast matching
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ms4.ms4_orchestrator import match_trial_to_patients
from src.ms4.patient_cache import get_patient_cache
from src.ms4.trial import Trial

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ============================================================================
# Configuration
# ============================================================================

MS3_BASE_URL = os.getenv("MS3_BASE_URL", "http://ms3:8003")
MS3_INIT_CHECK_TIMEOUT = int(os.getenv("MS3_INIT_CHECK_TIMEOUT", "120"))  # 2 minutes
MS3_INIT_CHECK_INTERVAL = int(os.getenv("MS3_INIT_CHECK_INTERVAL", "5"))  # Check every 5 seconds
MS4_STARTUP_RETRIES = int(os.getenv("MS4_STARTUP_RETRIES", "3"))
MS4_STARTUP_RETRY_DELAY = int(os.getenv("MS4_STARTUP_RETRY_DELAY", "5"))

# ============================================================================
# MS3 Initialization Status Check
# ============================================================================

async def wait_for_ms3_initialization(
    ms3_base_url: str,
    timeout_seconds: int = MS3_INIT_CHECK_TIMEOUT,
    check_interval: int = MS3_INIT_CHECK_INTERVAL
) -> bool:
    """
    Wait for MS3 to complete its initialization.
    
    Polls the MS3 initialization status endpoint until it reports success
    or timeout is reached.
    
    Args:
        ms3_base_url: Base URL for MS3 service
        timeout_seconds: Maximum time to wait (default: 120 seconds)
        check_interval: Seconds between status checks (default: 5 seconds)
    
    Returns:
        True if MS3 initialization is complete, False if timeout
    """
    logger.info("\n" + "=" * 80)
    logger.info("[MS3 WAIT] Waiting for MS3 to complete initialization...")
    logger.info(f"[MS3 WAIT] Timeout: {timeout_seconds}s, Check interval: {check_interval}s")
    logger.info("=" * 80)
    
    initialization_url = f"{ms3_base_url}/api/ms3/initialization-status"
    start_time = asyncio.get_event_loop().time()
    attempt = 0
    
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            attempt += 1
            elapsed = asyncio.get_event_loop().time() - start_time
            
            try:
                logger.info(f"[MS3 WAIT] Attempt {attempt}: Checking initialization status... (elapsed: {elapsed:.1f}s)")
                response = await client.get(initialization_url)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if initialization is complete
                    is_initialized = data.get("initialized", False)
                    is_ready = data.get("ready", False)
                    status = data.get("status", "unknown")
                    patients_loaded = data.get("patients_loaded", 0)
                    
                    logger.info(
                        f"[MS3 WAIT] Status: {status} | "
                        f"Initialized: {is_initialized} | "
                        f"Ready: {is_ready} | "
                        f"Patients: {patients_loaded}"
                    )
                    
                    if is_initialized and is_ready:
                        logger.info("=" * 80)
                        logger.info("[MS3 WAIT] ✓ MS3 initialization COMPLETE")
                        logger.info(f"[MS3 WAIT] Patients loaded in MS3: {patients_loaded}")
                        logger.info(f"[MS3 WAIT] Total wait time: {elapsed:.1f}s")
                        logger.info("=" * 80)
                        return True
                else:
                    logger.debug(f"[MS3 WAIT] Unexpected status code: {response.status_code}")
            
            except httpx.ConnectError as e:
                logger.warning(f"[MS3 WAIT] Connection error: {str(e)}")
            except httpx.TimeoutException as e:
                logger.warning(f"[MS3 WAIT] Timeout error: {str(e)}")
            except Exception as e:
                logger.warning(f"[MS3 WAIT] Error: {str(e)}")
            
            # Check if we've exceeded timeout
            if elapsed >= timeout_seconds:
                logger.error("=" * 80)
                logger.error(f"[MS3 WAIT] ✗ TIMEOUT: MS3 not initialized after {timeout_seconds}s")
                logger.error("[MS3 WAIT] Proceeding without MS3 data (requests will fail)")
                logger.error("=" * 80)
                return False
            
            # Wait before next check
            logger.info(f"[MS3 WAIT] Waiting {check_interval}s before next check...")
            await asyncio.sleep(check_interval)


# ============================================================================
# Patient Cache Loading with Retry
# ============================================================================

async def load_patients_with_retry(
    cache,
    max_attempts: int = 3,
    initial_delay: int = 5
) -> bool:
    """
    Load patients from MS3 with retry logic.
    
    Uses exponential backoff: first attempt immediately, then wait
    initial_delay, 2*initial_delay, 3*initial_delay, etc.
    
    Args:
        cache: PatientCache instance
        max_attempts: Number of retry attempts
        initial_delay: Initial delay between retries in seconds
    
    Returns:
        True if successful, False if all attempts fail
    """
    for attempt in range(1, max_attempts + 1):
        logger.info(f"\n[RETRY] Load attempt {attempt}/{max_attempts}")
        
        try:
            # Attempt to load patients
            success = await cache.load_all_patients()
            
            if success:
                logger.info(f"[RETRY] ✓ Attempt {attempt} succeeded")
                return True
            else:
                # Load failed, will retry
                logger.warning(
                    f"[RETRY] ✗ Attempt {attempt} failed: {cache.error}"
                )
                
                if attempt < max_attempts:
                    # Calculate backoff delay
                    delay = initial_delay * attempt
                    logger.info(
                        f"[RETRY] Waiting {delay} seconds before retry..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[RETRY] All {max_attempts} attempts exhausted")
                    return False
        
        except Exception as e:
            logger.error(f"[RETRY] Attempt {attempt} exception: {str(e)}")
            
            if attempt < max_attempts:
                delay = initial_delay * attempt
                logger.info(f"[RETRY] Waiting {delay} seconds before retry...")
                await asyncio.sleep(delay)
            else:
                logger.error("All retry attempts exhausted")
                return False
    
    return False


# ============================================================================
# Lifespan - Wait for MS3, then load patients
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager with MS3 initialization check.
    
    1. First: Wait for MS3 to complete its initialization
    2. Then: Load patient data from MS3 with retries
    3. Finally: Application is ready to accept requests
    """
    logger.info("\n" + "=" * 80)
    logger.info("MS4 APPLICATION STARTING")
    logger.info("=" * 80)
    
    # ========================================================================
    # Phase 1: Wait for MS3 initialization
    # ========================================================================
    
    ms3_ready = await wait_for_ms3_initialization(
        ms3_base_url=MS3_BASE_URL,
        timeout_seconds=MS3_INIT_CHECK_TIMEOUT,
        check_interval=MS3_INIT_CHECK_INTERVAL
    )
    
    if not ms3_ready:
        logger.warning("\n[STARTUP] MS3 initialization check timed out")
        logger.warning("[STARTUP] MS4 will attempt to load patients anyway...")
    
    # ========================================================================
    # Phase 2: Load patient cache from MS3 (with retries)
    # ========================================================================
    
    logger.info("\n[STARTUP] Initializing patient cache from MS3...")
    logger.info(f"[STARTUP] Retries enabled: {MS4_STARTUP_RETRIES} attempts, "
                f"{MS4_STARTUP_RETRY_DELAY}s initial delay")
    
    cache = get_patient_cache()
    
    # Set MS3 URL if different from default
    if MS3_BASE_URL != "http://ms3:8003":
        cache.ms3_base_url = MS3_BASE_URL
        logger.info(f"[STARTUP] Using custom MS3 URL: {MS3_BASE_URL}")
    
    success = await load_patients_with_retry(
        cache,
        max_attempts=MS4_STARTUP_RETRIES,
        initial_delay=MS4_STARTUP_RETRY_DELAY
    )
    
    # ========================================================================
    # Phase 3: Report final status
    # ========================================================================
    
    if success:
        stats = cache.get_cache_stats()
        logger.info("\n[STARTUP] ✓ SUCCESS - Patient cache loaded")
        logger.info(f" - Total patients: {stats['total_patients']}")
        logger.info(f" - Estimated memory: {stats['estimated_size_mb']} MB")
        logger.info(f" - Load time: {stats['load_time_seconds']} seconds")
        logger.info("=" * 80)
        logger.info("MS4 is ready to accept requests")
        logger.info("=" * 80 + "\n")
    else:
        logger.warning("\n[STARTUP] ✗ FAILURE - Patient cache failed to load after retries")
        logger.warning(f" - Error: {cache.error}")
        logger.warning(" - MS4 will still run but /match-trial endpoint will fail")
        logger.warning(" - Possible causes:")
        logger.warning(" 1. MS3 service is not running")
        logger.warning(" 2. MS3 database has no data yet")
        logger.warning(" 3. Network connectivity issue")
        logger.warning(" 4. MS3_BASE_URL is incorrect")
        logger.warning("=" * 80 + "\n")
    
    # Yield to let the app run
    yield
    
    logger.info("\n[SHUTDOWN] MS4 shutting down...")


# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="MS4 - Clinical Trial Patient Matcher",
    description="Matches patients to clinical trials with MS3 initialization awareness and cached patient data",
    version="2.3",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Pydantic Models
# ============================================================================

class TrialMatchRequest(BaseModel):
    """Request model for trial matching"""
    nct_id: str
    sort_by: str = "match_percentage"
    order: str = "descending"
    limit: Optional[int] = None
    min_match: Optional[float] = None


class PatientsAndTrialLegacy(BaseModel):
    """Request model for legacy /match endpoint"""
    rawpatients: str
    rawtrial: str


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    cache = get_patient_cache()
    return {
        "status": "healthy",
        "service": "MS4 - Patient Trial Matcher",
        "version": "2.3",
        "cache": {
            "is_loaded": cache.is_loaded,
            "patients_cached": cache.get_patient_count()
        }
    }


@app.get("/cache-status")
async def cache_status():
    """Get detailed cache status"""
    cache = get_patient_cache()
    stats = cache.get_cache_stats()
    return {
        "status": "ready" if stats["is_loaded"] else "not_loaded",
        "total_patients": stats["total_patients"],
        "estimated_memory_mb": stats["estimated_size_mb"],
        "load_time_seconds": stats["load_time_seconds"],
        "error": stats["error"]
    }


@app.get("/info")
async def get_info():
    """Get service information"""
    cache = get_patient_cache()
    return {
        "service": "MS4 - Clinical Trial Patient Matcher",
        "version": "2.3",
        "features": [
            "Waits for MS3 initialization before loading patients",
            "Bulk patient loading from MS3 at startup",
            "Retry logic for resilience",
            "In-memory patient caching for performance",
            "Trial matching using cached data (no redundant MS3 fetches)",
            "Batch trial-to-patient matching with ranking"
        ],
        "configuration": {
            "ms3_initialization_timeout_seconds": MS3_INIT_CHECK_TIMEOUT,
            "ms3_initialization_check_interval_seconds": MS3_INIT_CHECK_INTERVAL,
            "startup_retries": MS4_STARTUP_RETRIES,
            "startup_retry_delay_seconds": MS4_STARTUP_RETRY_DELAY,
            "ms3_base_url": MS3_BASE_URL
        },
        "cache_status": {
            "is_loaded": cache.is_loaded,
            "patients": cache.get_patient_count()
        }
    }


# ============================================================================
# Main Matching Endpoint - WITH CACHE OPTIMIZATION
# ============================================================================

@app.post("/match-trial")
async def match_trial_endpoint(request: TrialMatchRequest):
    """
    PRIMARY ENDPOINT: Match trial to all cached patients with ranking.
    
    KEY OPTIMIZATION: Uses in-memory cached patient data instead of
    fetching from MS3 for each request. This provides massive performance
    improvement when matching against 1000+ patients.
    
    Flow:
    1. Get all cached patients (1,097 in your case)
    2. Fetch trial criteria from MS2
    3. Evaluate each cached patient against trial criteria
    4. Score and rank results
    5. Return ranked matches
    
    Parameters:
        nct_id: Clinical trial ID (required)
        sort_by: "match_percentage" or "patient_id" (default: "match_percentage")
        order: "ascending" or "descending" (default: "descending")
        limit: Max number of results to return (default: all)
        min_match: Minimum match percentage threshold (0-100)
    
    Returns:
        Ranked list of matching patients with scores
    """
    cache = get_patient_cache()
    
    # Check if cache is loaded
    if not cache.is_loaded:
        logger.error(f"[MATCH] Cache not loaded. Error: {cache.error}")
        raise HTTPException(
            status_code=503,
            detail=f"Patient cache not ready. Error: {cache.error}. "
                   f"Check MS3 connection and restart MS4."
        )
    
    # Get all cached patient IDs
    patient_ids = cache.get_all_patient_ids()
    
    logger.info(f"[MATCH] Starting trial match: NCT={request.nct_id}, "
                f"patients={len(patient_ids)}, limit={request.limit}, "
                f"min_match={request.min_match}")
    
    try:
        # Call orchestrator with CACHED patients (not fetching from MS3)
        # This is the key optimization - pass cache.patients directly
        result = await match_trial_to_patients(
            nct_id=request.nct_id,
            patient_ids=patient_ids,
            cached_patients=cache.patients  # ← KEY: Use cached data!
        )
        
        # Extract matched patients
        trial_result = result.get("results", {})
        matched_patients = trial_result.get("matched_patients", [])
        
        logger.info(f"[MATCH] Trial {request.nct_id}: {len(matched_patients)} "
                    f"patients matched")
        
        # Filter by minimum match percentage
        if request.min_match is not None:
            matched_patients = [
                p for p in matched_patients
                if p.match_percentage >= request.min_match
            ]
        
        # Sort by specified field
        reverse_sort = request.order.lower() == "descending"
        
        if request.sort_by == "match_percentage":
            matched_patients.sort(key=lambda x: x.match_percentage,
                                reverse=reverse_sort)
        elif request.sort_by == "patient_id":
            matched_patients.sort(key=lambda x: x.patient_id,
                                reverse=reverse_sort)
        
        # Apply limit
        if request.limit:
            matched_patients = matched_patients[:request.limit]
        
        # Add ranks
        ranked_results = []
        for rank, patient in enumerate(matched_patients, 1):
            patient_dict = patient.__dict__.copy()
            patient_dict["rank"] = rank
            ranked_results.append(patient_dict)
        
        return {
            "nct_id": request.nct_id,
            "total_patients_searched": len(patient_ids),
            "matched_count": len(trial_result.get("matched_patients", [])),
            "results_returned": len(ranked_results),
            "filter_applied": {
                "sort_by": request.sort_by,
                "sort_order": request.order,
                "min_match_percentage": request.min_match,
                "limit": request.limit
            },
            "ranked_results": ranked_results
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[MATCH] Error during matching: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Trial matching failed: {str(e)}"
        )


@app.get("/debug/patient-structure")
async def debug_patient_structure():
    """Debug endpoint to inspect patient data structure"""
    cache = get_patient_cache()

    if not cache.is_loaded:
        raise HTTPException(status_code=503, detail="Cache not loaded")

    patient_ids = cache.get_all_patient_ids()
    if not patient_ids:
        raise HTTPException(status_code=400, detail="No patients in cache")

    patient = cache.patients[patient_ids[0]]

    return {
        "patient_id": patient_ids[0],
        "keys": list(patient.keys()),
        "structure": {
            key: {
                "type": type(val).__name__,
                "length": len(val) if isinstance(val, (list, dict)) else None,
                "first_item_keys": list(val[0].keys()) if isinstance(val, list) and val and isinstance(val[0],
                                                                                                       dict) else None,
                "sample": str(val)[:100] if not isinstance(val, (list, dict)) else None
            }
            for key, val in patient.items()
        }
    }


# ============================================================================
# Legacy Endpoint
# ============================================================================

@app.post("/match")
async def match_legacy(payload: PatientsAndTrialLegacy):
    """LEGACY ENDPOINT: Kept for backward compatibility"""
    logger.info("[LEGACY MATCH] Received request")
    
    try:
        patients = json.loads(payload.rawpatients)
    except json.JSONDecodeError as e:
        logger.error(f"[LEGACY MATCH] Invalid patients JSON: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Patients is not valid JSON: {e}"
        )
    
    try:
        trial = json.loads(payload.rawtrial)
    except json.JSONDecodeError as e:
        logger.error(f"[LEGACY MATCH] Invalid trial JSON: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Trial is not valid JSON: {e}"
        )
    
    logger.info(f"[LEGACY MATCH] Evaluating {len(patients)} patients")
    
    try:
        trial_obj = Trial(trial)
        trial_results = trial_obj.evaluate(patients)
    
    except ZeroDivisionError as e:
        return {
            "error": "Trial has no weight criteria",
            "message": str(e),
            "matched_patients": []
        }
    
    except Exception as e:
        logger.error(f"[LEGACY MATCH] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error evaluating trial: {str(e)}"
        )
    
    return {"results": trial_results}


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8004))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting MS4 server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

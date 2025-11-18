import asyncio
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

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

MS3_BASE_URL = os.getenv("MS3_BASE_URL", "http://ms3:8003")
MS3_INIT_CHECK_TIMEOUT = int(os.getenv("MS3_INIT_CHECK_TIMEOUT", "120"))  # 2 minutes
MS3_INIT_CHECK_INTERVAL = int(os.getenv("MS3_INIT_CHECK_INTERVAL", "5"))  # Check every 5 seconds
MS4_STARTUP_RETRIES = int(os.getenv("MS4_STARTUP_RETRIES", "3"))
MS4_STARTUP_RETRY_DELAY = int(os.getenv("MS4_STARTUP_RETRY_DELAY", "5"))


async def wait_for_ms3_initialization(
    ms3_base_url: str,
    timeout_seconds: int = MS3_INIT_CHECK_TIMEOUT,
    check_interval: int = MS3_INIT_CHECK_INTERVAL
) -> bool:
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


async def load_patients_with_retry(
    cache,
    max_attempts: int = 3,
    initial_delay: int = 5
) -> bool:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    load MS3 data into memory in MS4 as soon as MS3 is ready
    """
    logger.info("\n" + "=" * 80)
    logger.info("MS4 APPLICATION STARTING")
    logger.info("=" * 80)

    
    ms3_ready = await wait_for_ms3_initialization(
        ms3_base_url=MS3_BASE_URL,
        timeout_seconds=MS3_INIT_CHECK_TIMEOUT,
        check_interval=MS3_INIT_CHECK_INTERVAL
    )
    
    if not ms3_ready:
        logger.warning("\n[STARTUP] MS3 initialization check timed out")
        logger.warning("[STARTUP] MS4 will attempt to load patients anyway...")

    
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

# debug endpoints
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


@app.post("/match-trial")
async def match_trial_endpoint(request: TrialMatchRequest):
    return {
      "nct_id": "NCT06129539",
      "total_patients_searched": 1097,
      "matched_count": 1097,
      "results_returned": 10,
      "filter_applied": {
        "sort_by": "match_percentage",
        "sort_order": "descending",
        "min_match_percentage": 0,
        "limit": 10
      },
      "ranked_results": [
        {
          "patient_id": "d79f2406-212d-79d3-bcac-84592c75514c",
          "match_percentage": 87.5,
          "rank": 1,
          "matches": [True,False,True],
          "types": ["TypeA", "TypeB", "TypeC"],
          "fields": ["FieldA", "FieldB", "FieldC"],
          "operators": ["==", "<=", ">="],
          "values": ["good",5,10],
          "patient_values": ["good", 17, 22],
        },
        {
          "patient_id": "7c50b099-cfb9-64b4-a5cf-5481dd546d09",
          "match_percentage": 80.5,
          "rank": 2,
          "matches": [False, False,],
          "types": ["TypeA", "TypeB"],
          "fields": ["FieldA", "FieldB"],
          "operators": ["==", "<="],
          "values": ["bad", 5],
          "patient_values": ["good", 17],
        },
        {
          "patient_id": "a37071bf-99a8-e91b-5130-79505f8bac49",
          "match_percentage": 80.5,
          "rank": 3,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "15c1e3a5-f50e-2b54-14df-81f2605d9382",
          "match_percentage": 80.5,
          "rank": 4,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "9b1717c4-329a-150d-4193-a5ad5ed0af65",
          "match_percentage": 75.5,
          "rank": 5,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "70e51696-9f7f-cb78-7930-89c5dc212047",
          "match_percentage": 70.5,
          "rank": 6,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "fa47522a-591e-1bc6-fcbf-48ba5a36e2e8",
          "match_percentage": 65.5,
          "rank": 7,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "f5c268eb-6ccd-0ed2-2b60-967fb8f3e143",
          "match_percentage": 63.5,
          "rank": 8,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "51d1b218-4104-036e-8674-1d8dc4472031",
          "match_percentage": 64.5,
          "rank": 9,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        },
        {
          "patient_id": "befa5995-5fa6-33fb-ad58-41ccd7049f8f",
          "match_percentage": 0.5,
          "rank": 10,
          "matches": [],
          "types": [],
          "fields": [],
          "operators": [],
          "values": [],
          "patient_values": [],
        }
      ]
    }
    '''cache = get_patient_cache()
    
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
        )'''


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

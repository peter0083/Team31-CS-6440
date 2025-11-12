# ms4_orchestrator.py
"""
MS4 Orchestrator Module - Updated Version

Handles HTTP communication with MS2 (Trial Criteria) and MS3 (Patient Phenotypes)
Now supports using cached patient data to avoid redundant MS3 fetches
Transforms data formats and manages the complete matching workflow
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import HTTPException

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# Configuration
# ============================================================================

MS2_BASE_URL = os.getenv("MS2_BASE_URL", "http://ms2:8002")
MS3_BASE_URL = os.getenv("MS3_BASE_URL", "http://ms3:8003")

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Default meet percentage threshold (minimum % of criteria to meet)
DEFAULT_MEET_PERCENTAGE = 45

# ============================================================================
# HTTP Client Functions
# ============================================================================

async def fetch_trial_criteria(nct_id: str) -> Dict[str, Any]:
    """
    Fetch parsed trial criteria from MS2.
    
    Args:
        nct_id: Clinical trial ID (e.g., 'NCT05123456')
    
    Returns:
        Trial criteria object with inclusion/exclusion rules
    
    Raises:
        HTTPException: If MS2 request fails or NCT ID not found
    """
    try:
        url = f"{MS2_BASE_URL}/api/ms2/parsed-criteria/{nct_id}"
        logger.info(f"[MS2 FETCH] Fetching trial criteria: {url}")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url)
            
            if response.status_code == 404:
                logger.warning(f"[MS2 FETCH] Trial not found: {nct_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Trial criteria not found for NCT ID: {nct_id}"
                )
            
            response.raise_for_status()
            trial_data: Dict[str, Any] = response.json()
            logger.info(f"[MS2 FETCH] ✓ Successfully fetched criteria for {nct_id}")
            return trial_data
    
    except httpx.TimeoutException:
        logger.error(f"[MS2 FETCH] Timeout while fetching {nct_id}")
        raise HTTPException(
            status_code=504,
            detail=f"MS2 service timeout while fetching trial {nct_id}"
        )
    
    except httpx.HTTPError as e:
        logger.error(f"[MS2 FETCH] HTTP error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to MS2: {str(e)}"
        )


async def fetch_patient_phenotype(patient_id: str) -> Dict[str, Any]:
    """
    Fetch single patient phenotype from MS3.
    
    Args:
        patient_id: Patient ID (e.g., 'patient-001')
    
    Returns:
        Patient phenotype object with demographics, conditions, labs, medications, etc.
    
    Raises:
        HTTPException: If MS3 request fails or patient not found
    """
    try:
        url = f"{MS3_BASE_URL}/api/ms3/patient-phenotype/{patient_id}"
        logger.debug(f"[MS3 FETCH] Fetching patient phenotype: {url}")
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url)
            
            if response.status_code == 404:
                logger.warning(f"[MS3 FETCH] Patient not found: {patient_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Patient phenotype not found for ID: {patient_id}"
                )
            
            response.raise_for_status()
            phenotype: Dict[str, Any] = response.json()
            logger.debug(f"[MS3 FETCH] ✓ Fetched phenotype for {patient_id}")
            return phenotype
    
    except httpx.TimeoutException:
        logger.error(f"[MS3 FETCH] Timeout while fetching patient {patient_id}")
        raise HTTPException(
            status_code=504,
            detail=f"MS3 service timeout while fetching patient {patient_id}"
        )
    
    except httpx.HTTPError as e:
        logger.error(f"[MS3 FETCH] HTTP error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to MS3: {str(e)}"
        )


async def fetch_patient_phenotypes(patient_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch multiple patient phenotypes from MS3 concurrently.
    
    Args:
        patient_ids: List of patient IDs
    
    Returns:
        List of patient phenotype objects
    
    Raises:
        HTTPException: If any fetch fails (partial failures included)
    """
    logger.info(f"[MS3 FETCH] Fetching {len(patient_ids)} patient phenotypes from MS3")
    
    if not patient_ids:
        logger.warning("[MS3 FETCH] No patient IDs provided")
        return []
    
    patients: List[Dict[str, Any]] = []
    failed_patients: List[tuple[str, str]] = []
    
    # Create tasks for concurrent fetching
    tasks = [fetch_patient_phenotype(pid) for pid in patient_ids]
    
    try:
        results: List[Union[Dict[str, Any], BaseException]] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        
        for pid, result in zip(patient_ids, results):
            if isinstance(result, BaseException):
                failed_patients.append((pid, str(result)))
                logger.warning(f"[MS3 FETCH] Failed to fetch {pid}: {str(result)}")
            else:
                patients.append(result)
                logger.debug(f"[MS3 FETCH] Fetched phenotype for {pid}")
    
    except Exception as e:
        logger.error(f"[MS3 FETCH] Concurrent fetch error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch patients from MS3: {str(e)}"
        )
    
    if failed_patients:
        logger.warning(f"[MS3 FETCH] Failed to fetch {len(failed_patients)} patients")
        
        if len(failed_patients) == len(patient_ids):
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch all patients from MS3"
            )
    
    logger.info(f"[MS3 FETCH] ✓ Successfully fetched {len(patients)} out of {len(patient_ids)} patients")
    return patients


# ============================================================================
# Data Transformation Functions
# ============================================================================

def transform_ms3_phenotype_for_ms4(phenotype: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform MS3 phenotype format to MS4 expected format.
    
    MS3 output format:
        {
            "patient_id": "...",
            "demographics": {...},
            "conditions": [...],
            "lab_results": [...],
            ...
        }
    
    MS4 expected format:
        {
            "general": {
                "patient_id": "...",
                "demographics": {...}
            },
            "conditions": [...],
            "lab_results": [...],
            ...
        }
    
    Args:
        phenotype: MS3 phenotype output
    
    Returns:
        Transformed phenotype for MS4 matching
    """
    logger.debug(f"[TRANSFORM] Transforming phenotype for patient {phenotype.get('patient_id', 'unknown')}")
    
    transformed: Dict[str, Any] = {
        "general": {
            "patient_id": phenotype.get("patient_id"),
            "phenotype_timestamp": phenotype.get("phenotype_timestamp"),
            "demographics": phenotype.get("demographics", {})
        },
        "conditions": phenotype.get("conditions", []),
        "lab_results": phenotype.get("lab_results", []),
        "medications": phenotype.get("medications", []),
        "pregnancy_status": phenotype.get("pregnancy_status"),
        "smoking_status": phenotype.get("smoking_status"),
        "data_completeness": phenotype.get("data_completeness", {})
    }
    
    return transformed


async def fetch_and_transform_patients(
    patient_ids: List[str]
) -> List[Dict[str, Any]]:
    """
    Fetch patients from MS3 and transform to MS4 format.
    
    Args:
        patient_ids: List of patient IDs
    
    Returns:
        List of transformed patient phenotypes
    """
    logger.info(f"[TRANSFORM] Fetching and transforming {len(patient_ids)} patients")
    phenotypes = await fetch_patient_phenotypes(patient_ids)
    
    transformed = [
        transform_ms3_phenotype_for_ms4(phenotype)
        for phenotype in phenotypes
    ]
    
    logger.info(f"[TRANSFORM] ✓ Transformed {len(transformed)} patients for MS4")
    return transformed


# ============================================================================
# NEW: Cached Patient Functions
# ============================================================================

def transform_cached_patient_for_ms4(cached_phenotype: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform cached patient phenotype to MS4 expected format.
    Handles data already loaded in memory from MS3 cache.
    
    Args:
        cached_phenotype: Patient phenotype from cache
    
    Returns:
        Transformed phenotype for MS4 matching
    """
    patient_id = cached_phenotype.get("patient_id")
    logger.debug(f"[CACHE TRANSFORM] Transforming cached patient {patient_id}")
    
    # Check if already in MS4 format
    if "general" in cached_phenotype:
        logger.debug(f"[CACHE TRANSFORM] Patient {patient_id} already in MS4 format")
        return cached_phenotype
    
    # Transform from MS3/cached format to MS4 format
    transformed: Dict[str, Any] = {
        "general": {
            "patient_id": patient_id,
            "phenotype_timestamp": cached_phenotype.get("phenotype_timestamp"),
            "demographics": cached_phenotype.get("demographics", {})
        },
        "conditions": cached_phenotype.get("conditions", []),
        "lab_results": cached_phenotype.get("lab_results", []),
        "medications": cached_phenotype.get("medications", []),
        "pregnancy_status": cached_phenotype.get("pregnancy_status"),
        "smoking_status": cached_phenotype.get("smoking_status"),
        "data_completeness": cached_phenotype.get("data_completeness", {})
    }
    
    return transformed


async def get_patients_from_cache(
    patient_ids: List[str],
    cached_patients: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Get and transform patients from in-memory cache instead of fetching from MS3.
    This is MUCH faster than fetching from MS3 for each request.
    
    Args:
        patient_ids: List of patient IDs to retrieve
        cached_patients: Dictionary of patient_id -> phenotype (from PatientCache)
    
    Returns:
        List of transformed patient phenotypes ready for matching
    """
    logger.info(f"[CACHE] Retrieving {len(patient_ids)} patients from in-memory cache")
    
    transformed_patients: List[Dict[str, Any]] = []
    missing_patients: List[str] = []
    
    for patient_id in patient_ids:
        if patient_id in cached_patients:
            phenotype = cached_patients[patient_id]
            transformed = transform_cached_patient_for_ms4(phenotype)
            transformed_patients.append(transformed)
        else:
            missing_patients.append(patient_id)
    
    if missing_patients:
        logger.warning(f"[CACHE] {len(missing_patients)} patients not found in cache")
    
    logger.info(f"[CACHE] ✓ Retrieved {len(transformed_patients)} patients from cache")
    return transformed_patients


# ============================================================================
# Health Check Functions
# ============================================================================

async def check_ms2_health() -> Dict[str, Any]:
    """
    Check MS2 service health.
    
    Returns:
        Health status object
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{MS2_BASE_URL}/health")
            
            if response.status_code == 200:
                return {"status": "healthy", "service": "MS2"}
            
            return {"status": "unhealthy", "service": "MS2", "code": response.status_code}
    
    except Exception as e:
        logger.warning(f"[HEALTH] MS2 health check failed: {str(e)}")
        return {"status": "unreachable", "service": "MS2", "error": str(e)}


async def check_ms3_health() -> Dict[str, Any]:
    """
    Check MS3 service health.
    
    Returns:
        Health status object
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{MS3_BASE_URL}/live")
            
            if response.status_code == 200:
                data: Dict[str, Any] = response.json()
                return {"status": data.get("status", "unknown"), "service": "MS3"}
            
            return {"status": "unhealthy", "service": "MS3", "code": response.status_code}
    
    except Exception as e:
        logger.warning(f"[HEALTH] MS3 health check failed: {str(e)}")
        return {"status": "unreachable", "service": "MS3", "error": str(e)}


async def check_services_health() -> Dict[str, Dict[str, Any]]:
    """
    Check health of both MS2 and MS3.
    
    Returns:
        Health status for both services
    """
    logger.info("[HEALTH] Checking health of MS2 and MS3")
    ms2_health = await check_ms2_health()
    ms3_health = await check_ms3_health()
    
    return {
        "ms2": ms2_health,
        "ms3": ms3_health
    }


# ============================================================================
# Main Orchestration Functions
# ============================================================================

async def match_trial_to_patients(
    nct_id: str,
    patient_ids: List[str],
    cached_patients: Optional[Dict[str, Dict[str, Any]]] = None,
    meet_percentage: int = DEFAULT_MEET_PERCENTAGE
) -> Dict[str, Any]:
    """
    Main orchestration function: Fetch trial and patients, then match.
    
    OPTIMIZATION: If cached_patients is provided, uses in-memory data
    instead of fetching from MS3. This provides massive performance benefit
    for repeated matching requests.
    
    Args:
        nct_id: Clinical trial ID
        patient_ids: List of patient IDs to match
        cached_patients: Optional dict of patient_id -> phenotype from cache
                        If provided, avoids MS3 fetch (MUCH faster!)
        meet_percentage: Minimum percentage of criteria to meet (default: 45)
    
    Returns:
        Matching results with ranked patients
    
    Raises:
        HTTPException: If MS2 fetch fails or other errors occur
    """
    logger.info(f"[MATCH] Starting trial match for {nct_id}")
    logger.info(f"[MATCH] Patients: {len(patient_ids)}, Using cache: {cached_patients is not None}")
    
    try:
        # Step 1: Fetch trial criteria from MS2
        logger.info("[MATCH] Step 1/3: Fetching trial criteria from MS2")
        trial_data = await fetch_trial_criteria(nct_id)
        
        # Step 2: Get patient phenotypes (from cache or MS3)
        logger.info("[MATCH] Step 2/3: Getting patient phenotypes")
        if cached_patients is not None:
            logger.info("[MATCH] Using in-memory cache (fastest path)")
            patients = await get_patients_from_cache(patient_ids, cached_patients)
        else:
            logger.info("[MATCH] Fetching from MS3 (slower path)")
            patients = await fetch_and_transform_patients(patient_ids)
        
        if not patients:
            logger.warning("[MATCH] No patients could be retrieved")
            raise HTTPException(
                status_code=400,
                detail="No valid patient data could be retrieved"
            )
        
        # Step 3: Import Trial class and evaluate
        logger.info("[MATCH] Step 3/3: Evaluating matches")
        from src.ms4.trial import Trial
        
        trial = Trial(trial_data)
        results: Any = trial.evaluate(patients)
        
        logger.info(f"[MATCH] ✓ Successfully completed matching for {nct_id}")
        logger.info(f"[MATCH] Matched {len(results.get('matched_patients', []))} patients")
        
        return {
            "nct_id": nct_id,
            "num_patients": len(patients),
            "meet_percentage_threshold": meet_percentage,
            "results": results
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"[MATCH] Unexpected error during matching: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Matching failed: {str(e)}"
        )


async def match_trial_to_single_patient(
    nct_id: str,
    patient_id: str,
    cached_patients: Optional[Dict[str, Dict[str, Any]]] = None,
    meet_percentage: int = DEFAULT_MEET_PERCENTAGE
) -> Dict[str, Any]:
    """
    Match a single patient to a trial.
    
    Args:
        nct_id: Clinical trial ID
        patient_id: Patient ID to match
        cached_patients: Optional cache dict for faster lookup
        meet_percentage: Minimum percentage of criteria to meet (default: 45)
    
    Returns:
        Matching results for single patient
    """
    logger.info(f"[MATCH SINGLE] Starting single patient match: {patient_id} -> {nct_id}")
    
    result = await match_trial_to_patients(
        nct_id=nct_id,
        patient_ids=[patient_id],
        cached_patients=cached_patients,
        meet_percentage=meet_percentage
    )
    
    return result


# ============================================================================
# Batch Operations
# ============================================================================

async def match_trial_to_multiple_patients_batch(
    nct_id: str,
    patient_ids: List[str],
    cached_patients: Optional[Dict[str, Dict[str, Any]]] = None,
    batch_size: int = 10,
    meet_percentage: int = DEFAULT_MEET_PERCENTAGE
) -> Dict[str, Any]:
    """
    Match trial to multiple patients in batches (for very large patient lists).
    
    Uses cache if provided, otherwise fetches from MS3.
    
    Args:
        nct_id: Clinical trial ID
        patient_ids: List of patient IDs
        cached_patients: Optional cache dict (recommended for performance)
        batch_size: Number of patients per batch
        meet_percentage: Minimum percentage of criteria to meet
    
    Returns:
        Aggregated matching results
    """
    logger.info(f"[BATCH] Starting batch matching for {len(patient_ids)} patients")
    logger.info(f"[BATCH] Batch size: {batch_size}, Using cache: {cached_patients is not None}")
    
    all_results: List[Dict[str, Any]] = []
    failed_batches: List[Dict[str, Any]] = []
    
    # Fetch trial once
    trial_data = await fetch_trial_criteria(nct_id)
    
    from src.ms4.trial import Trial
    trial = Trial(trial_data)
    
    # Process in batches
    for i in range(0, len(patient_ids), batch_size):
        batch_ids = patient_ids[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        logger.info(f"[BATCH] Processing batch {batch_num}: {len(batch_ids)} patients")
        
        try:
            # Get patients from cache or MS3
            if cached_patients is not None:
                patients = await get_patients_from_cache(batch_ids, cached_patients)
            else:
                patients = await fetch_and_transform_patients(batch_ids)
            
            batch_results: Any = trial.evaluate(patients)
            all_results.extend(batch_results)
        
        except Exception as e:
            logger.error(f"[BATCH] Batch {batch_num} failed: {str(e)}")
            failed_batches.append({
                "batch": batch_num,
                "patient_ids": batch_ids,
                "error": str(e)
            })
    
    return {
        "nct_id": nct_id,
        "total_patients": len(patient_ids),
        "successful_matches": len(all_results),
        "failed_batches": len(failed_batches),
        "results": all_results,
        "batch_errors": failed_batches if failed_batches else None
    }


# ============================================================================
# Utility Functions
# ============================================================================

def validate_patient_ids(patient_ids: List[str]) -> bool:
    """Validate patient IDs list."""
    if not patient_ids:
        logger.warning("[VALIDATE] Empty patient IDs list")
        return False
    
    if not isinstance(patient_ids, list):
        logger.warning("[VALIDATE] patient_ids must be a list")
        return False
    
    if len(patient_ids) > 10000:
        logger.warning(f"[VALIDATE] Large patient list: {len(patient_ids)} patients (>10000)")
    
    return True


def validate_nct_id(nct_id: str) -> bool:
    """Validate NCT ID format."""
    if not nct_id or not isinstance(nct_id, str):
        return False
    
    # Basic validation - NCT IDs typically start with 'NCT' followed by 8 digits
    if nct_id.startswith("NCT") and len(nct_id) >= 11:
        return True
    
    return False

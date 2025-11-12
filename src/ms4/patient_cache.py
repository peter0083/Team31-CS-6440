# src/ms4/patient_cache.py - Fixed Version
"""
Patient caching system for MS4.
Loads all patients from MS3 at startup and stores in memory.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class PatientCache:
    """In-memory cache of all patients for fast searching"""
    
    def __init__(self, ms3_base_url: str = "http://ms3:8003"):
        """
        Initialize patient cache.
        
        Args:
            ms3_base_url: Base URL for MS3 service
        """
        self.ms3_base_url = ms3_base_url
        self.patients: Dict[str, Dict[str, Any]] = {}  # patient_id -> phenotype
        self.patient_ids: List[str] = []
        self.is_loaded = False
        self.error: Optional[str] = None
        self.load_time_seconds: float = 0.0
    
    async def load_all_patients(self) -> bool:
        """
        Load all patients from MS3 API in bulk.
        
        Called during MS4 startup via lifespan context manager.
        
        Returns:
            True if successful, False otherwise
        """
        import time
        start_time = time.time()
        
        logger.info("=" * 70)
        logger.info("[PATIENT CACHE] Starting bulk load of patients from MS3")
        logger.info("=" * 70)
        
        try:
            # Step 1: Get all patient IDs
            logger.info("[PATIENT CACHE] Step 1/2: Fetching all patient IDs...")
            patient_ids = await self._fetch_all_patient_ids()
            
            if not patient_ids:
                self.error = "No patients found in MS3"
                logger.error(f"[PATIENT CACHE] ✗ {self.error}")
                return False
            
            self.patient_ids = patient_ids
            logger.info(f"[PATIENT CACHE] Found {len(patient_ids)} patients in database")
            
            # Step 2: Batch fetch phenotypes
            logger.info(f"[PATIENT CACHE] Step 2/2: Fetching phenotypes for {len(patient_ids)} patients...")
            await self._batch_fetch_phenotypes(patient_ids, batch_size=10)
            
            self.is_loaded = True
            self.load_time_seconds = time.time() - start_time
            
            logger.info("=" * 70)
            logger.info(f"[PATIENT CACHE] ✓ Successfully loaded {len(self.patients)} patients")
            logger.info(f"[PATIENT CACHE] ✓ Estimated cache size: ~{len(self.patients) * 3.3 / 1024:.1f} MB")
            logger.info(f"[PATIENT CACHE] ✓ Load time: {self.load_time_seconds:.2f} seconds")
            logger.info("=" * 70)
            
            return True
        
        except Exception as e:
            self.error = str(e)
            logger.error("=" * 70)
            logger.error(f"[PATIENT CACHE] ✗ Failed to load patients: {str(e)}")
            logger.error("=" * 70)
            return False
    
    async def _fetch_all_patient_ids(self) -> List[str]:
        """
        Fetch all patient IDs from MS3 using pagination.
        
        Returns:
            List of all patient IDs
        """
        patient_ids: List[str] = []
        offset = 0
        limit = 100
        
        logger.info(f"[PATIENT CACHE] Fetching patient IDs from MS3 with pagination (limit={limit})...")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while True:
                    url = f"{self.ms3_base_url}/api/ms3/patients?limit={limit}&offset={offset}"
                    logger.debug(f"[PATIENT CACHE] Fetching from: {url}")
                    
                    try:
                        response = await client.get(url)
                        response.raise_for_status()
                        patients = response.json()
                        
                        if not patients:
                            logger.debug(f"[PATIENT CACHE] No more patients at offset {offset}")
                            break
                        
                        for p in patients:
                            patient_id = p.get("patient_id") or p.get("id")
                            if patient_id:
                                patient_ids.append(patient_id)
                        
                        logger.info(f"[PATIENT CACHE] Fetched {len(patient_ids)} patient IDs so far...")
                        offset += limit
                    
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            logger.debug(f"[PATIENT CACHE] No more patients (404 at offset {offset})")
                            break
                        raise
            
            logger.info(f"[PATIENT CACHE] Total patient IDs fetched: {len(patient_ids)}")
            return patient_ids
        
        except Exception as e:
            logger.error(f"[PATIENT CACHE] Error fetching patient IDs: {str(e)}")
            raise
    
    async def _batch_fetch_phenotypes(
        self,
        patient_ids: List[str],
        batch_size: int = 10
    ) -> None:
        """
        Fetch phenotypes in batches to avoid overwhelming MS3.
        
        Uses concurrent requests within each batch.
        
        Args:
            patient_ids: List of all patient IDs
            batch_size: Number of concurrent requests per batch
        """
        total = len(patient_ids)
        successful = 0
        failed = 0
        
        logger.info(f"[PATIENT CACHE] Batch fetching phenotypes (batch_size={batch_size})...")
        
        async with httpx.AsyncClient(timeout=30) as client:
            for i in range(0, total, batch_size):
                batch = patient_ids[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total + batch_size - 1) // batch_size
                
                logger.info(f"[PATIENT CACHE] Batch {batch_num}/{total_batches}: Fetching {len(batch)} phenotypes...")
                
                # Create concurrent tasks for this batch
                tasks = [
                    self._fetch_patient_phenotype(client, pid)
                    for pid in batch
                ]
                
                # Run tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for patient_id, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"[PATIENT CACHE] Failed to fetch {patient_id}: {result}")
                        failed += 1
                    else:
                        self.patients[patient_id] = result
                        successful += 1
                
                # Log progress
                progress_pct = (min(i + batch_size, total) / total) * 100
                logger.info(f"[PATIENT CACHE] Progress: {min(i + batch_size, total)}/{total} ({progress_pct:.1f}%) - "
                           f"Successful: {successful}, Failed: {failed}")
        
        logger.info(f"[PATIENT CACHE] Batch fetch complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            logger.warning(f"[PATIENT CACHE] Warning: {failed} patient phenotypes could not be fetched")
    
    async def _fetch_patient_phenotype(
        self,
        client: httpx.AsyncClient,
        patient_id: str
    ) -> Dict[str, Any]:
        """
        Fetch single patient phenotype from MS3.
        
        Args:
            client: HTTPX async client
            patient_id: Patient ID
        
        Returns:
            Patient phenotype dictionary
        """
        url = f"{self.ms3_base_url}/api/ms3/patients/{patient_id}/phenotype"
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single cached patient phenotype.
        
        Args:
            patient_id: Patient ID
        
        Returns:
            Patient phenotype or None if not found
        """
        return self.patients.get(patient_id)
    
    def get_all_patients(self) -> List[Dict[str, Any]]:
        """
        Get all cached patients.
        
        Returns:
            List of all patient phenotypes
        """
        return list(self.patients.values())
    
    def get_all_patient_ids(self) -> List[str]:
        """
        Get all patient IDs.
        
        Returns:
            List of all patient IDs
        """
        return self.patient_ids.copy()
    
    def get_patient_count(self) -> int:
        """
        Get number of loaded patients.
        
        Returns:
            Number of patients in cache
        """
        return len(self.patients)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        return {
            "is_loaded": self.is_loaded,
            "total_patients": len(self.patients),
            "error": self.error,
            "estimated_size_mb": round(len(self.patients) * 3.3 / 1024, 2),
            "load_time_seconds": round(self.load_time_seconds, 2)
        }


# Global cache instance
_patient_cache: PatientCache = PatientCache()


def get_patient_cache() -> PatientCache:
    """
    Get the global patient cache instance.
    
    Returns:
        Global PatientCache instance
    """
    return _patient_cache

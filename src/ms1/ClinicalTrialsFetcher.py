"""
MS1 Microservice: Clinical Trials Data Fetcher

Fetches clinical trial data from local JSON files first, then ClinicalTrials.gov API if not found.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

import httpx
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ──────────────────────────────
# Setup Logging
# ──────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
app = FastAPI(title="ClinicalTrials Data Fetcher")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend origin in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────
# Models
# ──────────────────────────────

class SearchQuery(BaseModel):
    """Request model for search endpoint."""
    term: str


# ──────────────────────────────
# API Configuration
# ──────────────────────────────

CLINICAL_TRIALS_URL = "https://clinicaltrials.gov/api/v2/studies"
MAX_TRIALS = 5

# Data directory paths - Navigate to repo root
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "app" / "data" / "ms1"

# Supported conditions with local JSON files
SUPPORTED_CONDITIONS = ["diabetes", "dementia", "cancer"]

# Get MS2 URL from environment, fallback to localhost for development
MS2_URL = os.getenv("MS2_URL", "http://ms2:8002/api/ms2/receive")
logger.info(f"✅ MS2_URL configured: {MS2_URL}")
logger.info(f"📁 Data directory: {DATA_DIR}")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


# ──────────────────────────────
# Helper Functions
# ──────────────────────────────

def load_local_trial_data(condition: str) -> Optional[dict[str, Any]]:
    """
    Load trial data from local JSON file in data/ms1/ folder.

    Args:
        condition: The condition name (e.g., 'diabetes', 'dementia', 'cancer')

    Returns:
        The parsed JSON data if file exists, None otherwise
    """
    json_file = DATA_DIR / f"{condition.lower()}.json"

    if not json_file.exists():
        logger.warning(f"⚠️ Local file not found: {json_file}")
        return None

    try:
        with open(json_file, 'r') as f:
            data = cast(dict[str, Any], json.load(f))
        logger.info(f"✅ Loaded local trial data from: {json_file}")
        logger.info(f"📊 Found {len(data.get('studies', []))} studies in local file")
        return data
    except Exception as e:
        logger.error(f"❌ Error loading local trial data: {e}")
        return None


def save_payload_to_json(payload: dict, search_term: str) -> str:
    """
    Save API payload to JSON file in data/ms1/ folder for future use.

    Args:
        payload: The API response payload to save
        search_term: The search term used for the query

    Returns:
        Path to the saved JSON file
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = DATA_DIR / f"clinical_trials_{search_term.replace(' ', '_')}_{timestamp}.json"

    try:
        with open(filename, 'w') as f:
            json.dump(payload, f, indent=2)
        logger.info(f"✅ Saved API payload to {filename}")
        logger.info(f"💾 File is now available for future searches (replace {search_term}.json to use as mock)")
        return str(filename)
    except Exception as e:
        logger.error(f"❌ Failed to save payload to JSON: {e}")
        return ""


def fetch_with_retries(
        url: str,
        params: dict,
        max_retries: int = 3,
        timeout: int = 10
) -> Optional[requests.Response]:
    """
    Fetch data from ClinicalTrials.gov API with retry logic.

    Args:
        url: The API endpoint URL
        params: Query parameters
        max_retries: Maximum number of retries
        timeout: Request timeout in seconds

    Returns:
        Response object if successful, None otherwise
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Attempt {attempt + 1}/{max_retries} - Fetching from ClinicalTrials.gov")
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            logger.info("✅ Successfully fetched data from ClinicalTrials.gov API")
            return response
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout on attempt {attempt + 1}")
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Request failed on attempt {attempt + 1}: {e}")
            time.sleep(2 ** attempt)

    logger.error(f"❌ Failed to fetch after {max_retries} attempts")
    return None


async def send_to_ms2(trials: list[dict[str, Any]]) -> bool:
    """
    Send extracted trial data to MS2 for processing.

    Args:
        trials: List of trial dictionaries

    Returns:
        True if successful, False otherwise
    """
    if not trials:
        logger.warning("⚠️ No trials to send to MS2")
        return False

    try:
        logger.info(f"📤 Sending {len(trials)} trial(s) to MS2 at {MS2_URL}")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                MS2_URL,
                json=trials,
                headers={"Content-Type": "application/json"}
            )

        response.raise_for_status()
        logger.info("✅ Successfully sent data to MS2")
        logger.debug(f"MS2 response: {response.json()}")
        return True
    except httpx.ConnectError as e:
        logger.error(f"🔥 Connection error sending to MS2: {e}")
        logger.error(f"Make sure MS2 is running at {MS2_URL}")
        return False
    except httpx.TimeoutException as e:
        logger.error(f"⏱️ Timeout sending to MS2: {e}")
        return False
    except httpx.HTTPError as e:
        logger.error(f"🔥 HTTP error sending to MS2: {e}")
        return False
    except Exception as e:
        logger.error(f"🔥 Unexpected error sending to MS2: {e}")
        return False


def extract_trial_data(studies: list[dict]) -> list[dict[str, Any]]:
    """
    Extract and structure trial data from ClinicalTrials.gov response.

    Args:
        studies: Raw studies from API response

    Returns:
        List of structured trial dictionaries
    """
    extracted = []
    ingestion_ts = datetime.now(timezone.utc).isoformat()

    for study in studies:
        try:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            sponsor = protocol.get("sponsorCollaboratorsModule", {})
            locations = protocol.get("contactsLocationsModule", {})
            eligibility = protocol.get("eligibilityModule", {})
            design = protocol.get("designModule", {})
            interventions = protocol.get("armsInterventionsModule", {})

            # Safely extract location
            location_list = locations.get("locations", [])
            if location_list:
                location_obj = location_list[0]
                location = f"{location_obj.get('city', '')}, {location_obj.get('state', '')}"
            else:
                location = "Not specified"

            # Safely extract intervention
            interventions_list = interventions.get("interventions", [])
            intervention = interventions_list[0].get("name", "Not specified") if interventions_list else "Not specified"

            trial = {
                "nct_id": identification.get("nctId"),
                "title": identification.get("briefTitle"),
                "phase": design.get("phases", []),
                "sponsor": sponsor.get("leadSponsor", {}).get("name"),
                "location": location,
                "recruitment_status": status.get("overallStatus"),
                "eligibility_criteria": {
                    "raw_text": eligibility.get("eligibilityCriteria", "")
                },
                "study_population": eligibility.get("studyPopulation"),
                "intervention": intervention,
                "ingestion_timestamp": ingestion_ts
            }

            extracted.append(trial)
        except Exception as e:
            logger.warning(f"⚠️ Error extracting trial data: {e}")
            continue

    return extracted


# ──────────────────────────────
# API Endpoints
# ──────────────────────────────

@app.post("/search-trials")
async def search_trials(query: SearchQuery) -> dict[str, Any]:
    """
    Search for clinical trials from local JSON files first, then ClinicalTrials.gov API.

    Workflow:
    1. Validate search term against supported conditions
    2. Try to load from local JSON file in data/ms1/ first
    3. If not found locally, fetch from ClinicalTrials.gov API
    4. Save API response to data/ms1/ for future use
    5. Extract and structure data
    6. Send to MS2 for processing
    7. Return results to UI

    Args:
        query: SearchQuery with 'term' field

    Returns:
        Dict with trials data, counts, and data source

    Raises:
        HTTPException: If search term is not supported or processing fails
    """
    term = query.term.strip().lower()

    # Validate search term against supported conditions
    if term not in SUPPORTED_CONDITIONS:
        logger.warning(f"❌ Unsupported search term: {term}")
        raise HTTPException(
            status_code=400,
            detail=f"Search term must be one of: {', '.join(SUPPORTED_CONDITIONS)}"
        )

    logger.info(f"🔍 Searching for: {term}")

    # Try to load from local JSON file first
    data = load_local_trial_data(term)
    data_source = "local_file"

    # If not found locally, fetch from ClinicalTrials.gov API
    if data is None:
        logger.info(f"📡 Local file not found, fetching from ClinicalTrials.gov API for: {term}")
        data_source = "clinicaltrials_gov_api"

        # Build API parameters
        params = {
            "query.term": term,
            "filter.overallStatus": "RECRUITING",
            "query.locn": "United+States",
            "format": "json",
            "pageSize": 20,
        }

        # Fetch from ClinicalTrials.gov
        response = fetch_with_retries(CLINICAL_TRIALS_URL, params)
        if not response:
            logger.error("❌ Failed to fetch data from ClinicalTrials.gov")
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch data from ClinicalTrials.gov after multiple retries."
            )

        # Parse response
        data = response.json()

        # Save raw payload to JSON file in data/ms1/ for future use
        save_payload_to_json(data, term)

    # Extract studies from data
    studies = data.get("studies", [])[:MAX_TRIALS]

    if not studies:
        logger.info(f"❌ No results found for term: {term}")
        return {
            "message": f"No clinical trials found for '{term}'.",
            "trials": [],
            "count": 0,
            "data_source": data_source
        }

    logger.info(f"✅ Found {len(studies)} trials from {data_source}")

    # Extract trial data
    extracted_trials = extract_trial_data(studies)

    # Send to MS2 asynchronously (non-blocking)
    try:
        ms2_success = await send_to_ms2(extracted_trials)
        ms2_status = "sent" if ms2_success else "queued"
        logger.info(f"📊 MS2 status: {ms2_status}")
    except Exception as e:
        logger.warning(f"⚠️ Background MS2 send failed (non-blocking): {e}")
        ms2_status = "pending"

    # Return data to UI immediately
    return {
        "message": f"✅ Found {len(extracted_trials)} recruiting clinical trials",
        "count": len(extracted_trials),
        "trials": extracted_trials,
        "search_term": term,
        "data_source": data_source,
        "ms2_status": ms2_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Clinical Trials Data Fetcher (MS1)",
        "data_dir": str(DATA_DIR),
        "supported_conditions": SUPPORTED_CONDITIONS,
        "ms2_endpoint": MS2_URL,
        "supported_conditions_files": {
            "diabetes": (DATA_DIR / "diabetes.json").exists(),
            "dementia": (DATA_DIR / "dementia.json").exists(),
            "cancer": (DATA_DIR / "cancer.json").exists(),
        }
    }


@app.get("/docs-info")
async def docs_info() -> dict[str, Any]:
    """API information endpoint."""
    return {
        "title": "Clinical Trials Data Fetcher",
        "version": "1.0.0",
        "description": "Fetches clinical trial data from local JSON files (data/ms1/) or ClinicalTrials.gov API",
        "supported_conditions": SUPPORTED_CONDITIONS,
        "data_flow": {
            "1_user_selects": "User selects 'diabetes', 'dementia', or 'cancer' from dropdown in App.jsx",
            "2_fetch_local": "MS1 checks for diabetes.json, dementia.json, or cancer.json in data/ms1/",
            "3_fallback": "If not found, fetches from ClinicalTrials.gov API",
            "4_save": "Saves API response to data/ms1/ with timestamp for future use",
            "5_extract": "Extracts and structures trial data",
            "6_send_ms2": "Sends data to MS2 for processing",
            "7_return": "Returns results to React frontend"
        },
        "endpoints": {
            "POST /search-trials": "Search for trials by condition",
            "GET /health": "Health check with file status",
            "GET /docs": "Interactive API documentation (Swagger UI)"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

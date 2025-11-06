import logging
import time
from datetime import datetime, timezone

import httpx
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ──────────────────────────────
# Setup Logging
# ──────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
    term: str

# ──────────────────────────────
# API Configuration
# ──────────────────────────────
CLINICAL_TRIALS_URL = "https://clinicaltrials.gov/api/v2/studies"
MS2_URL = "http://127.0.0.1:8002/receive"
MAX_TRIALS = 5

HEADERS = {
    "User-Agent": (
        "PostmanRuntime/7.49.0"
    ),
    "Accept": "application/json",
}

# ──────────────────────────────
# Helper: Safe GET with retries
# ──────────────────────────────
def fetch_with_retries(url, params, retries=3, backoff=2):
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response
            logging.warning(f"⚠️ Attempt {attempt+1}: Status {response.status_code}")
        except Exception as e:
            logging.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
        time.sleep(backoff * (attempt + 1))
    return None

# ──────────────────────────────
# POST endpoint
# ──────────────────────────────
@app.post("/search-trials")
async def search_trials(query: SearchQuery, request: Request):
    term = query.term.strip()

    # Basic validation
    if not term.replace(" ", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid search term. Use only letters or numbers.")

    params = {
        "query.term": term,
        "filter.overallStatus": "RECRUITING",
        "query.locn": "United+States",
        "format": "json",
        "pageSize": 20,
    }

    logging.info(f"🔍 Searching ClinicalTrials.gov for: {term}")

    response = fetch_with_retries(CLINICAL_TRIALS_URL, params)
    if not response:
        raise HTTPException(status_code=500, detail="Failed to fetch data after multiple retries.")

    data = response.json()
    studies = data.get("studies", [])[:MAX_TRIALS]

    if not studies:
        logging.info("❌ No results found")
        return JSONResponse({"message": f"No results found for '{term}'. Please modify your search term."})

    extracted = []
    ing_ts = datetime.now(timezone.utc).isoformat()

    for study in studies:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        locations = protocol.get("contactsLocationsModule", {})
        eligibility = protocol.get("eligibilityModule", {})
        design = protocol.get("designModule", {})
        interventions = protocol.get("armsInterventionsModule", {})

        extracted.append({
            "nct_id": identification.get("nctId"),
            "title": identification.get("briefTitle"),
            "phase": design.get("phases", []),
            #"NumPhases": len(design.get("phases", [])),
            "sponsor": sponsor.get("leadSponsor", {}).get("name"),
            "location": locations.get("locations", [{}])[0].get("city") + ", " + locations.get("locations", [{}])[0].get("state"),
            #"LocationCountry": locations.get("locations", [{}])[0].get("country"),
            "recruitment_status": status.get("overallStatus"),
            "eligibility_criteria": {
                "raw_text": eligibility.get("eligibilityCriteria"),
            },
            "study_population": eligibility.get("studyPopulation"),
            "intervention": interventions.get("interventions", [{}])[0].get("name"),
            "ingestion_timestamp": ing_ts
        })
        print(extracted)
    try:
        # Stream result to MS2
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(MS2_URL, json=extracted)

        return {"message": "✅ Data fetched successfully", "count": len(extracted)}

    except Exception as e:
        logging.exception("🔥 Error sending data to MS2")
        raise HTTPException(status_code=500, detail=str(e))

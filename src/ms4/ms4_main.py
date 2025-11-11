import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ms4.trial import Trial

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: not secure at all but other settings don't seem to work
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PatientsAndTrial(BaseModel):
    rawpatients: str
    rawtrial: str


@app.post("/match")
def evaluate_trial(payload: PatientsAndTrial) -> dict:
    try:
        patients = json.loads(payload.rawpatients)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Patients is not valid JSON: {e}")

    try:
        trial = json.loads(payload.rawtrial)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Trial is not valid JSON: {e}")

    # debug MS3 data
    print("=== RECEIVED MS3 DATA ===")
    print(f"First patient keys: {list(patients[0].keys()) if patients else 'No patients'}")
    print(f"First patient: {json.dumps(patients[0], indent=2) if patients else 'No patients'}")
    print(f"Trial keys: {list(trial.keys())}")
    print("=== END DEBUG ===")

    try:
        trial_obj = Trial(trial)
        trial_results = trial_obj.evaluate(patients)
    except ZeroDivisionError as e:
        return {"error": "Trial has no weight criteria", "message": str(e), "matched_patients": []}
    except KeyError as e:
        return {"error": f"Missing data field: {e}", "matched_patients": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating trial: {str(e)}")

    return {"results": {trial_results}}
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.ms4.trial import Trial

app = FastAPI()


class PatientsAndTrial(BaseModel):
    raw_patients: str
    raw_trial: str


@app.post("/match")
def evaluate_trial(payload: PatientsAndTrial):
    try:
        patients = json.loads(payload.raw_patients)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"patients is not valid JSON: {e.msg}")

    try:
        trial = json.loads(payload.raw_trial)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"trial is not valid JSON: {e.msg}")

    trial = Trial(trial)
    trial_results = trial.evaluate(patients)

    result_str = json.dumps(trial_results)
    return {"result": result_str}

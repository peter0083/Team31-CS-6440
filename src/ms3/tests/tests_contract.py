import json, pathlib, requests, jsonschema

SCHEMA = {
  "$schema":"https://json-schema.org/draft/2020-12/schema",
  "type":"object",
  "required":["patient_id","phenotype_timestamp","demographics","conditions","lab_results","medications","pregnancy_status","smoking_status","data_completeness"],
  "properties":{
    "patient_id":{"type":"string"},
    "phenotype_timestamp":{"type":"string"},
    "demographics":{"type":"object"},
    "conditions":{"type":"array"},
    "lab_results":{"type":"array"},
    "medications":{"type":"array"},
    "pregnancy_status":{"type":"string"},
    "smoking_status":{"type":"string"},
    "data_completeness":{"type":"object"}
  }
}

def test_live():
    r = requests.get("http://localhost:8001/live", timeout=5)
    assert r.status_code == 200

def test_patient_example_contract():
    r = requests.get("http://localhost:8001/api/ms3/patient-phenotype/patient-001", timeout=5)
    assert r.status_code in (200,404)
    if r.status_code == 200:
        jsonschema.validate(r.json(), SCHEMA)

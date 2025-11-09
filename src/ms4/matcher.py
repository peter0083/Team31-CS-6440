'''import time

from fastapi import FastAPI
from pydantic import BaseModel

from src.ms4.trial import Trial

app = FastAPI()

sample_trial_data = {
    "nct_id": "NCT05123456",
    "parsing_timestamp": "2025-10-09T18:00:00Z",
    "inclusion_criteria": [
        {
            "rule_id": "inc_001",
            "type": "demographic",
            "identifier": ["age"],
            "field": "age",
            "operator": "between",
            "value": [18, 65],
            "unit": "years",
            "raw_text": "Age 18-65 years",
        },
        {
            "rule_id": "inc_002",
            "type": "lab_result",
            "identifier": ["test", "HbA1c"],
            "field": "value",
            "operator": ">=",
            "value": [7.0],
            "unit": "%",
            "raw_text": "HbA1c ≥ 7.0%",
        },
    ],
    "exclusion_criteria": [
        {
            "rule_id": "exc_001",
            "type": "condition",
            "identifier": ["pregnancy_status"],
            "field": "pregnancy_status",
            "operator": "==",
            "value": ["pregnant"],
            "raw_text": "Pregnant women",
        }
    ],
}

patients = [
    {
        "general": {
            "patient_id": "patient-001",
            "phenotype_timestamp": "2025-10-09T18:00:00Z",
            "demographics": {
                "age": 26,
                "gender": "female",
                "race": "White",
                "ethnicity": "Not Hispanic or Latino",
            },
        },
        "conditions": [
            {
                "code_system": "ICD-10",
                "code": "E11",
                "description": "Type 2 diabetes mellitus",
                "onset_date": "2020-03-15",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "pregnancy_status": "not_pregnant",
            },
            {
                "smoking_status": "never_smoker",
            },
        ],
        "lab_results": [
            {
                "test": "HbA1c",
                "value": 8.2,
                "unit": "%",
                "date": "2025-09-15",
                "reference_range": "4.0-5.6",
                "status": "final",
            },
            {
                "test": "Creatinine",
                "value": 1.1,
                "unit": "mg/dL",
                "date": "2025-09-15",
                "reference_range": "0.6-1.2",
            },
        ],
        "medications": [
            {
                "name": "Metformin",
                "generic_name": "metformin hydrochloride",
                "dosage": "500mg",
                "frequency": "twice daily",
                "start_date": "2020-03-20",
                "status": "active",
            }
        ],
        "pregnancy_status": "not_pregnant",
        "smoking_status": "never_smoker",
        "data_completeness": {
            "overall_score": 0.85,
            "demographics_score": 1.0,
            "conditions_score": 0.9,
            "labs_score": 0.8,
            "medications_score": 0.95,
            "missing_fields": ["family_history", "allergies"],
        },
    },
    {
        "general": {
            "patient_id": "patient-002",
            "phenotype_timestamp": "2025-10-09T18:00:00Z",
            "demographics": {
                "age": 19,
                "gender": "female",
                "race": "White",
                "ethnicity": "Not Hispanic or Latino",
            },
        },
        "conditions": [
            {
                "code_system": "ICD-10",
                "code": "E11",
                "description": "Type 2 diabetes mellitus",
                "onset_date": "2020-03-15",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "pregnancy_status": "pregnant",
            },
            {
                "smoking_status": "never_smoker",
            },
        ],
        "lab_results": [
            {
                "test": "HbA1c",
                "value": 10.6,
                "unit": "%",
                "date": "2025-09-15",
                "reference_range": "4.0-5.6",
                "status": "final",
            },
            {
                "test": "Creatinine",
                "value": 1.1,
                "unit": "mg/dL",
                "date": "2025-09-15",
                "reference_range": "0.6-1.2",
            },
        ],
        "medications": [
            {
                "name": "Metformin",
                "generic_name": "metformin hydrochloride",
                "dosage": "500mg",
                "frequency": "twice daily",
                "start_date": "2020-03-20",
                "status": "active",
            }
        ],
        "data_completeness": {
            "overall_score": 0.85,
            "demographics_score": 1.0,
            "conditions_score": 0.9,
            "labs_score": 0.8,
            "medications_score": 0.95,
            "missing_fields": ["family_history", "allergies"],
        },
    },
    {
        "general": {
            "patient_id": "patient-003",
            "phenotype_timestamp": "2025-10-09T18:00:00Z",
            "demographics": {
                "age": 99,
                "gender": "female",
                "race": "White",
                "ethnicity": "Not Hispanic or Latino",
            },
        },
        "conditions": [
            {
                "code_system": "ICD-10",
                "code": "E11",
                "description": "Type 2 diabetes mellitus",
                "onset_date": "2020-03-15",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
        ],
        "lab_results": [
            {
                "test": "HbA1c",
                "value": 8.2,
                "unit": "%",
                "date": "2025-09-15",
                "reference_range": "4.0-5.6",
                "status": "final",
            },
            {
                "test": "Creatinine",
                "value": 1.1,
                "unit": "mg/dL",
                "date": "2025-09-15",
                "reference_range": "0.6-1.2",
            },
        ],
        "medications": [
            {
                "name": "Metformin",
                "generic_name": "metformin hydrochloride",
                "dosage": "500mg",
                "frequency": "twice daily",
                "start_date": "2020-03-20",
                "status": "active",
            }
        ],
        "data_completeness": {
            "overall_score": 0.85,
            "demographics_score": 1.0,
            "conditions_score": 0.9,
            "labs_score": 0.8,
            "medications_score": 0.95,
            "missing_fields": ["family_history", "allergies"],
        },
    },
    {
        "general": {
            "patient_id": "patient-004",
            "phenotype_timestamp": "2025-10-09T18:00:00Z",
            "demographics": {
                "age": 44,
                "gender": "female",
                "race": "White",
                "ethnicity": "Not Hispanic or Latino",
            },
        },
        "conditions": [
            {
                "code_system": "ICD-10",
                "code": "E11",
                "description": "Type 2 diabetes mellitus",
                "onset_date": "2020-03-15",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "pregnancy_status": "not_pregnant",
            },
            {
                "smoking_status": "never_smoker",
            },
        ],
        "lab_results": [
            {
                "test": "Creatinine",
                "value": 1.1,
                "unit": "mg/dL",
                "date": "2025-09-15",
                "reference_range": "0.6-1.2",
            }
        ],
        "medications": [
            {
                "name": "Metformin",
                "generic_name": "metformin hydrochloride",
                "dosage": "500mg",
                "frequency": "twice daily",
                "start_date": "2020-03-20",
                "status": "active",
            }
        ],
        "pregnancy_status": "not_pregnant",
        "smoking_status": "never_smoker",
        "data_completeness": {
            "overall_score": 0.85,
            "demographics_score": 1.0,
            "conditions_score": 0.9,
            "labs_score": 0.8,
            "medications_score": 0.95,
            "missing_fields": ["family_history", "allergies"],
        },
    },
    {
        "general": {
            "patient_id": "patient-005",
            "phenotype_timestamp": "2025-10-09T18:00:00Z",
            "demographics": {
                "age": 3,
                "gender": "female",
                "race": "White",
                "ethnicity": "Not Hispanic or Latino",
            },
        },
        "conditions": [
            {
                "code_system": "ICD-10",
                "code": "E11",
                "description": "Type 2 diabetes mellitus",
                "onset_date": "2020-03-15",
                "status": "active",
            },
            {
                "code_system": "ICD-10",
                "code": "I10",
                "description": "Essential hypertension",
                "onset_date": "2021-06-20",
                "status": "active",
            },
            {
                "pregnancy_status": "not_pregnant",
            },
            {
                "smoking_status": "never_smoker",
            },
        ],
        "lab_results": [
            {
                "test": "Creatinine",
                "value": 1.1,
                "unit": "mg/dL",
                "date": "2025-09-15",
                "reference_range": "0.6-1.2",
            }
        ],
        "medications": [
            {
                "name": "Metformin",
                "generic_name": "metformin hydrochloride",
                "dosage": "500mg",
                "frequency": "twice daily",
                "start_date": "2020-03-20",
                "status": "active",
            }
        ],
        "pregnancy_status": "not_pregnant",
        "smoking_status": "never_smoker",
        "data_completeness": {
            "overall_score": 0.85,
            "demographics_score": 1.0,
            "conditions_score": 0.9,
            "labs_score": 0.8,
            "medications_score": 0.95,
            "missing_fields": ["family_history", "allergies"],
        },
    },
]

def print_dots(count: int = 3, delay: float = 0.25, end: str = "\n") -> None:
    """Print `count` dots, pausing `delay` seconds between each."""
    for _ in range(count):
        print(".", end="", flush=True)
        time.sleep(delay)
    print(end, end="")

    def main() -> None:
    # print_dots(3, 0.25)
    trial_json = sample_trial_data
    trial = Trial(trial_json)
    trial.set_meet_percentage(45)
    json = trial.evaluate(patients)
    print(json)
    
if __name__ == "__main__":
    main()
'''





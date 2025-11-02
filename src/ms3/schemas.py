# schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class Demographics(BaseModel):
    age: int = Field(..., example=45)
    gender: str = Field(..., example="female")
    race: str = Field(..., example="White")
    ethnicity: str = Field(..., example="Not Hispanic or Latino")

class Condition(BaseModel):
    code_system: str = Field(..., example="ICD-10")
    code: str = Field(..., example="E11")
    description: str = Field(..., example="Type 2 diabetes mellitus")
    onset_date: Optional[str] = Field(None, example="2020-03-15")
    status: Optional[str] = Field(None, example="active")

class LabResult(BaseModel):
    test: str = Field(..., example="HbA1c")
    value: Optional[float] = Field(None, example=8.2)
    unit: Optional[str] = Field(None, example="%")
    date: Optional[str] = Field(None, example="2025-09-15")
    reference_range: Optional[str] = Field(None, example="4.0-5.6")
    status: Optional[str] = Field(None, example="final")

class Medication(BaseModel):
    name: str = Field(..., example="Metformin")
    generic_name: Optional[str] = Field("", example="metformin hydrochloride")
    dosage: Optional[str] = Field("", example="500mg")
    frequency: Optional[str] = Field("", example="twice daily")
    start_date: Optional[str] = Field(None, example="2020-03-20")
    status: Optional[str] = Field(None, example="active")

class DataCompleteness(BaseModel):
    overall_score: float = Field(..., example=0.85)
    demographics_score: float = Field(..., example=1.0)
    conditions_score: float = Field(..., example=0.9)
    labs_score: float = Field(..., example=0.8)
    medications_score: float = Field(..., example=0.95)
    missing_fields: List[str] = Field(default_factory=list, example=["family_history","allergies"])

class Phenotype(BaseModel):
    patient_id: str = Field(..., example="patient-001")
    phenotype_timestamp: str = Field(..., example="2025-10-09T18:00:00Z")
    demographics: Demographics
    conditions: List[Condition]
    lab_results: List[LabResult]
    medications: List[Medication]
    pregnancy_status: str = Field(..., example="not_pregnant")
    smoking_status: str = Field(..., example="never_smoker")
    data_completeness: DataCompleteness

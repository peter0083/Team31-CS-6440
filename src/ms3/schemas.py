from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: int = Field(default=0, ge=0)
    gender: Optional[str] = None
    race: Optional[str] = None
    ethnicity: Optional[str] = None


class Condition(BaseModel):
    code_system: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    onset_date: Optional[str] = None
    status: Optional[str] = None


class LabResult(BaseModel):
    test: str
    value: Optional[float] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = None


class Medication(BaseModel):
    name: str
    generic_name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[str] = None
    status: Optional[str] = None


class DataCompleteness(BaseModel):
    overall_score: float
    demographics_score: float
    conditions_score: float
    labs_score: float
    medications_score: float
    missing_fields: List[str] = Field(default_factory=list)


class Phenotype(BaseModel):
    patient_id: str
    phenotype_timestamp: str
    demographics: Demographics
    conditions: List[Condition] = Field(default_factory=list)
    lab_results: List[LabResult] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    pregnancy_status: str
    smoking_status: str
    data_completeness: DataCompleteness

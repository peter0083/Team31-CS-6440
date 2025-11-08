# schemas.py
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field


class Demographics(BaseModel):
    age: Annotated[int, Field(examples=[45])]
    gender: Annotated[str, Field(examples=["female"])]
    race: Annotated[str, Field(examples=["White"])]
    ethnicity: Annotated[str, Field(examples=["Not Hispanic or Latino"])]

class Condition(BaseModel):
    code_system: Annotated[str, Field(examples=["ICD-10"])]
    code: Annotated[str, Field(examples=["E11"])]
    description: Annotated[str, Field(examples=["Type 2 diabetes mellitus"])]
    onset_date: Optional[str] = Field(None, examples=["2020-03-15"])
    status: Optional[str] = Field(None, examples=["active"])

class LabResult(BaseModel):
    test: Annotated[str, Field(examples=["HbA1c"])]
    value: Optional[float] = Field(None, examples=[8.2])
    unit: Optional[str] = Field(None, examples=["%"])
    date: Optional[str] = Field(None, examples=["2025-09-15"])
    reference_range: Optional[str] = Field(None, examples=["4.0-5.6"])
    status: Optional[str] = Field(None, examples=["final"])

class Medication(BaseModel):
    name: Annotated[str, Field(examples=["Metformin"])]
    generic_name: Optional[str] = Field("", examples=["metformin hydrochloride"])
    dosage: Optional[str] = Field("", examples=["500mg"])
    frequency: Optional[str] = Field("", examples=["twice daily"])
    start_date: Optional[str] = Field(None, examples=["2020-03-20"])
    status: Optional[str] = Field(None, examples=["active"])

class DataCompleteness(BaseModel):
    overall_score: Annotated[float, Field(examples=[0.85])]
    demographics_score: Annotated[float, Field(examples=[1.0])]
    conditions_score: Annotated[float, Field(examples=[0.9])]
    labs_score: Annotated[float, Field(examples=[0.8])]
    medications_score: Annotated[float, Field(examples=[0.95])]
    missing_fields: List[str] = Field(default_factory=list, examples=[["family_history", "allergies"]])

class Phenotype(BaseModel):
    patient_id: Annotated[str, Field(examples=["patient-001"])]
    phenotype_timestamp: Annotated[str, Field(examples=["2025-10-09T18:00:00Z"])]
    demographics: Demographics
    conditions: List[Condition]
    lab_results: List[LabResult]
    medications: List[Medication]
    pregnancy_status: Annotated[str, Field(examples=["not_pregnant"])]
    smoking_status: Annotated[str, Field(examples=["never_smoker"])]
    data_completeness: DataCompleteness



from datetime import date, datetime
from typing import Annotated, List, Optional, Union

from pydantic import BaseModel, Field

# =========================================================
# DEMOGRAPHICS (with age)
# =========================================================

class Demographics(BaseModel):
    """Patient demographic information including age calculated from birth date."""
    patient_id: Annotated[str, Field(examples=["patient-001"])]
    birth_date: Optional[date] = Field(None, examples=["1940-01-01"])
    age: Optional[int] = Field(None, examples=[84])
    gender: Optional[str] = Field(None, examples=["male"])
    race: Optional[str] = Field(None, examples=["American Indian or Alaska Native"])
    ethnicity: Optional[str] = Field(None, examples=["Not Hispanic or Latino"])


# =========================================================
# CONDITION
# =========================================================

class Condition(BaseModel):
    """Clinical condition diagnosed for a patient."""
    condition_id: Annotated[str, Field(examples=["cond-001"])]
    code: Optional[str] = Field(None, examples=["224299000"])
    code_system: Optional[str] = Field(None, examples=["http://snomed.info/sct"])
    description: Optional[str] = Field(None, examples=["Received higher education (finding)"])
    onset_date_time: Optional[Union[datetime, str]] = Field(None, examples=["2020-01-15T10:30:00"])
    clinical_status: Optional[str] = Field(None, examples=["active"])


# =========================================================
# LAB RESULT (OBSERVATION)
# =========================================================

class LabResult(BaseModel):
    """Laboratory observation result for a patient."""
    observation_id: Annotated[str, Field(examples=["obs-001"])]
    code: Optional[str] = Field(None, examples=["4548-4"])
    code_system: Optional[str] = Field(None, examples=["http://loinc.org"])
    display: Optional[str] = Field(None, examples=["Hemoglobin A1c/Hemoglobin.total in Blood"])
    value: Optional[float] = Field(None, examples=[7.5])
    unit: Optional[str] = Field(None, examples=["%"])
    effective_date_time: Optional[Union[datetime, str]] = Field(None, examples=["2020-06-15T10:30:00"])
    reference_range_text: Optional[str] = Field(None, examples=["4.0-6.0"])
    status: Optional[str] = Field(None, examples=["final"])


# =========================================================
# MEDICATION
# =========================================================

class Medication(BaseModel):
    """Medication request for a patient."""
    medication_id: Annotated[str, Field(examples=["med-001"])]
    name: Optional[str] = Field(None, examples=["Naproxen sodium 220 MG Oral Tablet"])
    generic_name: Optional[str] = Field(None, examples=["Naproxen sodium"])
    dose: Optional[str] = Field(None, examples=["220 MG"])
    frequency: Optional[str] = Field(None, examples=["Twice daily"])
    authored_on: Optional[Union[datetime, str]] = Field(None, examples=["2020-01-15T10:30:00"])
    status: Optional[str] = Field(None, examples=["active"])


# =========================================================
# PHENOTYPE (COMPLETE PATIENT PROFILE)
# =========================================================

class Phenotype(BaseModel):
    """Complete patient phenotype profile including demographics, conditions, labs, and medications."""
    patient_id: str
    demographics: Demographics
    conditions: List[Condition] = []
    lab_results: List[LabResult] = []
    medications: List[Medication] = []

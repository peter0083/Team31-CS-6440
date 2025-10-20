"""Data models for MS2 microservice: clinical trial criteria parser."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ExampleRequest:
    pass


class ExampleResponse:
    pass

class ErrorResponse(BaseModel):
    detail: str


class EligibilityCriteria(BaseModel):
    raw_text: str


class InclusionCriteriaRule(BaseModel):
    rule_id: str
    type: str
    field: str
    operator: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    code_system: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    raw_text: str


class ExclusionCriteriaRule(BaseModel):
    rule_id: str
    type: str
    field: str
    value: Optional[str] = None
    severity: Optional[str] = None
    raw_text: str


class ParsedCriteriaResponse(BaseModel):
    nct_id: str
    parsing_timestamp: datetime
    inclusion_criteria: List[InclusionCriteriaRule]
    exclusion_criteria: List[ExclusionCriteriaRule]
    parsing_confidence: float
    total_rules_extracted: int

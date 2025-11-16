from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InclusionCriteriaRule(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier")
    type: str = Field(..., description="Type of rule (demographic, condition, lab_value, etc.)")
    identifier: List[str] = Field(default_factory=list, description="Keywords/tags identifying this rule")
    field: str = Field(..., description="Field name or category")
    operator: Optional[str] = Field(None, description="Comparison operator")
    value: Optional[Any] = Field(None, description="Expected value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    description: str = Field(..., description="Human-readable description")
    raw_text: str = Field(..., description="Original text from criteria")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence")
    code_system: Optional[str] = Field(None, description="Medical coding system")
    code: Optional[str] = Field(None, description="Medical code")

class ExclusionCriteriaRule(BaseModel):
    rule_id: str = Field(..., description="Unique rule identifier")
    type: str = Field(..., description="Type of rule")
    identifier: List[str] = Field(default_factory=list, description="Keywords/tags identifying this rule")
    field: str = Field(..., description="Field name or category")
    operator: Optional[str] = Field(None, description="Comparison operator")
    value: Optional[Any] = Field(None, description="Expected value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    description: str = Field(..., description="Human-readable description")
    raw_text: str = Field(..., description="Original text from criteria")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence")
    code_system: Optional[str] = Field(None, description="Medical coding system")
    code: Optional[str] = Field(None, description="Medical code")

class ReasoningStep(BaseModel):
    step: int = Field(..., description="Step number")
    description: str = Field(..., description="Reasoning description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Step confidence")

class ParsedCriteriaResponse(BaseModel):
    nct_id: str = Field(..., description="NCT identifier")
    parsing_timestamp: datetime = Field(..., description="When parsing occurred")
    inclusion_criteria: List[InclusionCriteriaRule] = Field(default_factory=list)
    exclusion_criteria: List[ExclusionCriteriaRule] = Field(default_factory=list)
    parsing_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    total_rules_extracted: int = Field(..., ge=0, description="Total number of rules")
    model_used: str = Field(..., description="LLM model used")
    reasoning_steps: Optional[List[ReasoningStep]] = Field(None, description="Reasoning steps")

class EligibilityCriteria(BaseModel):
    raw_text: str = Field(..., description="Raw eligibility criteria text")

class TrialDataFromMS1(BaseModel):
    nct_id: str
    title: str
    eligibility_criteria: Dict[str, Any]
    status: str
    phase: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    llm_provider: str
    database_connected: bool
    redis_connected: bool
    uptime_seconds: float


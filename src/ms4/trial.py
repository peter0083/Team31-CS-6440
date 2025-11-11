
from src.ms4.criteria import Criteria
from src.ms4.reasoningstep import ReasoningStep
from src.ms4.scoredpatient import ScoredPatient


class Trial:
    def __init__(self, trial_data: dict) -> None:
        self.nct_id: str = trial_data.get("nct_id", "")
        self.parsing_timestamp: str = trial_data.get("parsing_timestamp", "")
        
        # Fix 1: Handle None for inclusion_criteria
        inclusion_criteria = trial_data.get("inclusion_criteria")
        if inclusion_criteria is not None and isinstance(inclusion_criteria, list):
            self.inclusion_criteria: list[Criteria] = []
            for crit in inclusion_criteria:
                rule_id = crit.get("rule_id")
                crit_type = crit.get("type")
                identifier = crit.get("identifier")
                field = crit.get("field")
                operator = crit.get("operator")
                value = crit.get("value")
                raw_text = crit.get("raw_text")
                description = crit.get("description") if "description" in crit else None
                confidence = crit.get("confidence") if "confidence" in crit else 0.0
                coding_system = crit.get("coding_system") if "coding_system" in crit else None
                coding = crit.get("coding") if "coding" in crit else None
                unit = crit.get("unit") if "unit" in crit else None

                self.inclusion_criteria.append(
                    Criteria(
                        crit_rule_id=rule_id,
                        crit_type=crit_type,
                        crit_identifier=identifier,
                        crit_field=field,
                        crit_operator=operator,
                        crit_value=value,
                        raw_text=raw_text,
                        description=description or "",  # FIX: Convert None to ""
                        confidence=confidence,
                        coding_system=coding_system or "",  # FIX: Convert None to ""
                        code=coding or "",  # FIX: Convert None to ""
                        unit=unit or "",  # FIX: Convert None to ""
                    )
                )
        else:
            self.inclusion_criteria = []

        # Fix 2: Handle None for exclusion_criteria
        exclusion_criteria = trial_data.get("exclusion_criteria")
        if exclusion_criteria is not None and isinstance(exclusion_criteria, list):
            self.exclusion_criteria: list[Criteria] = []
            for crit in exclusion_criteria:
                rule_id = crit.get("rule_id")
                crit_type = crit.get("type")
                identifier = crit.get("identifier")
                field = crit.get("field")
                operator = crit.get("operator")
                value = crit.get("value")
                raw_text = crit.get("raw_text")
                description = crit.get("description") if "description" in crit else None
                confidence = crit.get("confidence") if "confidence" in crit else 0.0
                coding_system = crit.get("coding_system") if "coding_system" in crit else None
                coding = crit.get("coding") if "coding" in crit else None
                unit = crit.get("unit") if "unit" in crit else None

                self.exclusion_criteria.append(
                    Criteria(
                        crit_rule_id=rule_id,
                        crit_type=crit_type,
                        crit_identifier=identifier,
                        crit_field=field,
                        crit_operator=operator,
                        crit_value=value,
                        raw_text=raw_text,
                        description=description or "",  # FIX: Convert None to ""
                        confidence=confidence,
                        coding_system=coding_system or "",  # FIX: Convert None to ""
                        code=coding or "",  # FIX: Convert None to ""
                        unit=unit or "",  # FIX: Convert None to ""
                    )
                )
        else:
            self.exclusion_criteria = []

    def get_total_weight(self) -> float:
        """Calculate total weight of all active inclusion criteria."""
        total: float = 0.0
        for crit in self.inclusion_criteria:
            if crit.active:
                total += crit.weight
        return total

    def evaluate(self, patients: list[dict]) -> dict:
        """
        Evaluate patients against trial inclusion/exclusion criteria.
        
        Args:
            patients: List of patient phenotype dictionaries
            
        Returns:
            Dictionary with matched patients and evaluation results
        """
        matched_patients: list[ScoredPatient] = []
        
        for patient in patients:
            # Check exclusion criteria first
            excluded: bool = False
            for excl_crit in self.exclusion_criteria:
                meets_exclusion, _ = excl_crit.meets(patient)
                if meets_exclusion:
                    excluded = True
                    break
            
            if excluded:
                continue
            
            # Evaluate inclusion criteria
            total: float = 0.0
            matched_criteria: list[ReasoningStep] = []
            
            for incl_crit in self.inclusion_criteria:
                if not incl_crit.active:
                    continue
                    
                meets_criteria, reason = incl_crit.meets(patient)
                if meets_criteria:
                    total += incl_crit.weight
                    matched_criteria.append(
                        ReasoningStep(
                            criterion_id=incl_crit.rule_id,
                            criterion_text=incl_crit.raw_text,
                            patient_value=str(reason),
                            match_result=True,
                        )
                    )
            
            # Calculate percentage match
            total_weight = self.get_total_weight()
            if total_weight == 0:
                percentage: float = 0.0  # No weight criteria to evaluate
            else:
                percentage = 100 * total / total_weight
            
            # Only add if there's some match or if inclusion criteria exist
            if percentage > 0 or len(self.inclusion_criteria) == 0:
                # FIX: Handle None for patient_id - ensure it's a string
                patient_id: str = patient.get("patient_id") or patient.get("id") or "unknown"
                matched_patients.append(
                    ScoredPatient(
                        patient_id=patient_id,
                        match_percentage=percentage,
                        reasoning_steps=matched_criteria,
                    )
                )
        
        return {
            "trial_id": self.nct_id,
            "matched_patients_count": len(matched_patients),
            "matched_patients": matched_patients,
        }

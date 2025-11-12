# src/ms4/trial.py - Fixed Version
"""
Trial class for evaluating patient-trial compatibility.
Simplified version that works with the actual data structure.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PatientMatch(BaseModel):
    """Result of matching a patient to a trial"""
    patient_id: str
    match_percentage: float


class Trial:
    """Represents a clinical trial with eligibility criteria"""
    
    def __init__(self, trial_data: Dict[str, Any]):
        self.nct_id = trial_data.get("nct_id", "UNKNOWN")
        self.inclusion_criteria = trial_data.get("inclusion_criteria", [])
        self.exclusion_criteria = trial_data.get("exclusion_criteria", [])
        logger.info(f"[TRIAL] {self.nct_id}: {len(self.inclusion_criteria)} inclusion, {len(self.exclusion_criteria)} exclusion")
    
    def evaluate(self, patients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate patients against trial criteria"""
        logger.info(f"[TRIAL] Evaluating {len(patients)} patients")
        
        matched_patients: List[PatientMatch] = []
        
        for patient in patients:
            try:
                match = self._evaluate_patient(patient)
                if match:
                    matched_patients.append(match)
            except Exception as e:
                logger.warning(f"[TRIAL] Error: {e}")
                continue
        
        matched_patients.sort(key=lambda x: x.match_percentage, reverse=True)
        logger.info(f"[TRIAL] Found {len(matched_patients)} matches")
        
        return {
            "trial_nct_id": self.nct_id,
            "total_patients_evaluated": len(patients),
            "matched_patients": matched_patients,
            "total_matched": len(matched_patients),
        }
    
    def _evaluate_patient(self, patient: Dict[str, Any]) -> Optional[PatientMatch]:
        """Evaluate a single patient"""
        patient_id = patient.get("patient_id", "UNKNOWN")
        
        # For now, evaluate based on demographic criteria only
        # since conditions/labs/medications are empty
        
        inclusion_met = 0
        inclusion_total = len(self.inclusion_criteria)
        
        for criterion in self.inclusion_criteria:
            if self._matches_criterion(patient, criterion):
                inclusion_met += 1
        
        if inclusion_total == 0:
            match_percentage = 100.0
        else:
            match_percentage = (inclusion_met / inclusion_total) * 100.0
        
        # Only return patients with >0% match
        if match_percentage > 0:
            return PatientMatch(
                patient_id=patient_id,
                match_percentage=round(match_percentage, 2)
            )

        return None
    
    def _matches_criterion(self, patient: Dict[str, Any], criterion: Dict[str, Any]) -> bool:
        """Check if patient matches a single criterion"""
        try:
            criterion_type = criterion.get("type", "")
            field = criterion.get("field", "")
            operator = criterion.get("operator", "=")
            value = criterion.get("value")
            
            # Skip header/metadata rows (null values, generic identifiers)
            if value is None:
                return True  # Neutral
            
            # Demographic criteria (age, gender, etc.)
            if criterion_type == "demographic":
                demographics = patient.get("demographics", {})
                patient_value = demographics.get(field)
                
                if patient_value is None:
                    return False
                
                # Age comparisons
                if field == "age":
                    try:
                        pv = int(patient_value)
                        vv = int(value)
                        if operator == ">=":
                            return pv >= vv
                        elif operator == "<=":
                            return pv <= vv
                        elif operator == ">":
                            return pv > vv
                        elif operator == "<":
                            return pv < vv
                        elif operator == "=":
                            return pv == vv
                    except (ValueError, TypeError):
                        return False
                
                # String comparisons (gender, race, etc.)
                else:
                    pv_str = str(patient_value).lower()
                    v_str = str(value).lower()
                    if operator == "=":
                        return pv_str == v_str
                    elif operator == "!=":
                        return pv_str != v_str
                    else:  # If operator is neither "=" nor "!="
                        return False
            
            # Condition/diagnosis (empty in current data)
            elif criterion_type == "condition":
                conditions = patient.get("conditions", [])
                if not conditions:
                    # Neutral - can't evaluate with no data
                    return True
                
                identifier = criterion.get("identifier", [])
                search_term = " ".join([str(x).lower() for x in identifier]) if identifier else str(value).lower()
                
                for cond in conditions:
                    cond_str = str(cond).lower()
                    if search_term in cond_str:
                        return True
                return False
            
            # Other criterion types - neutral (can't evaluate)
            else:
                return True
        
        except Exception as e:
            logger.debug(f"[CRITERION] Error: {e}")
            return True  # Neutral on error

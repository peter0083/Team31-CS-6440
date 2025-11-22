import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from src.ms4.criteria import Criteria

logger = logging.getLogger(__name__)


class PatientMatch(BaseModel):
    """Result of matching a patient to a trial"""
    patient_id: str
    match_percentage: float
    isInclusion: List[bool]
    matches: List[bool]
    types: List[str]
    fields: List[str]
    operators: List[str]
    values: List[str]
    patient_values: List[str]


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
        isInclusion = []
        matches = []
        types = []
        fields = []
        operators = []
        values = []
        patient_values = []
        """Evaluate a single patient"""
        logger.info(f"[DEBUG] Patient keys: {list(patient.keys())}")
        if 'conditions' in patient:
            logger.info(f"[DEBUG] aaPatient conditions: {patient['conditions']}")
        logger.info(f"[DEBUG] Patient data sample: {str(patient)[:200]}")
        logger.info(f"[DEBUG] Criteria length: {len(self.inclusion_criteria)}")

        # patient data is nested under "general"
        patient_id = patient.get("general", {}).get("patient_id", "UNKNOWN")

        logger.info(f"[DEBUG] Extracted patient_id: {patient_id}")

        inclusion_met = 0
        inclusion_total = len(self.inclusion_criteria)
        
        for criterion in self.inclusion_criteria:
            match_results = self._matches_criterion(patient,criterion)
            if match_results[0]:
                inclusion_met += 1
            isInclusion.append(True)
            matches.append(match_results[0])
            types.append(match_results[1])
            fields.append(match_results[2])
            operators.append(match_results[3])
            values.append(match_results[4])
            patient_values.append(match_results[5])

        for criterion in self.exclusion_criteria:
            match_results = self._matches_criterion(patient,criterion)
            if match_results[0]:
                inclusion_met = 0
            isInclusion.append(False)
            matches.append(match_results[0])
            types.append(match_results[1])
            fields.append(match_results[2])
            operators.append(match_results[3])
            values.append(match_results[4])
            patient_values.append(match_results[5])


        match_percentage = (inclusion_met / inclusion_total) * 100.0
        
        # Only return patients with >0% match
        #if match_percentage > 0:
        return PatientMatch(
            patient_id=patient_id,
            match_percentage=round(match_percentage, 4),
            isInclusion=isInclusion,
            matches = matches,
            types = types,
            fields = fields,
            operators = operators,
            values = values,
            patient_values = patient_values,
        )


        return None
    
    def _matches_criterion(self, patient: Dict[str, Any], criterion: Dict[str, Any]) -> Tuple[bool,str,str,str,str,str]:
        """Check if patient matches a single criterion"""
        try:
            criterion_type = criterion.get("type", "")
            field = criterion.get("field", "")
            operator = criterion.get("operator", "=")
            value = criterion.get("value")
            
            # Skip header/metadata rows (null values, generic identifiers)
            if value is None:
                #Changed to False (neutral should not qualify)
                return False,criterion_type,field,operator, "None", "Not Pulled"  # Neutral
            
            # Demographic criteria (age, gender, etc.)
            if criterion_type == "demographic":
                # demographics is also nested under general
                demographics = patient.get("general", {}).get("demographics", {})
                patient_value = demographics.get(field)
                
                if patient_value is None:
                    return False,criterion_type,field,operator, value, "NA"

                # Age comparisons
                if field == "gender":
                    try:
                        pv = str(patient_value)
                        vv = str(value)
                        if value == "all":
                            return True, criterion_type, field, operator, value, patient_value
                        else:
                            return pv == vv, criterion_type, field, operator, value, patient_value
                    except (ValueError, TypeError):
                        logger.info(
                            f"[CRITERION] Match Error 1: field {field} operator {operator} value {value} patient value {patient_value}")
                        return False, criterion_type, field, operator, value, "Value / Type Error"

                # Pregnancy status
                '''if field == "pregnancy_satus":
                    try:
                        pv = str(patient_value)
                        vv = str(value)
                        return pv == vv, criterion_type, field, operator, value, patient_value
                    except (ValueError, TypeError):
                        logger.info(
                            f"[CRITERION] Match Error 1: field {field} operator {operator} value {value} patient value {patient_value}")
                        return False, criterion_type, field, operator, value, "Value / Type Error"'''

                # Age comparisons
                if field == "age":
                    try:
                        pv = int(patient_value)
                        vv = int(value)
                        if vv == "NA":
                            return True, criterion_type, field, operator, value, patient_value
                        if operator == ">=":
                            return pv >= vv,criterion_type,field,operator,value,patient_value
                        elif operator == "<=":
                            return pv <= vv,criterion_type,field,operator,value,patient_value
                        elif operator == ">":
                            return pv > vv,criterion_type,field,operator,value,patient_value
                        elif operator == "<":
                            return pv < vv,criterion_type,field,operator,value,patient_value
                        elif operator == "=":
                            return pv == vv,criterion_type,field,operator,value,patient_value
                        else:
                            return False,criterion_type,field,operator,value,patient_value
                    except (ValueError, TypeError):
                        logger.info(f"[CRITERION] Match Error 1: field {field} operator {operator} value {value} patient value {patient_value}")
                        return False,criterion_type,field,operator,value,"Value / Type Error"
                
                # String comparisons (gender, race, etc.)
                else:
                    pv_str = str(patient_value).lower()
                    v_str = str(value).lower()
                    if operator == "=":
                        return pv_str == v_str,criterion_type,field,operator,value,patient_value
                    elif operator == "!=":
                        return pv_str != v_str,criterion_type,field,operator,value,patient_value
                    else:  # If operator is neither "=" nor "!="
                        return False,criterion_type,field,operator,value,patient_value
            
            # Condition/diagnosis (empty in current data)
            elif criterion_type == "condition":
                logger.info(f"[DEBUG] In Conditions...")
                conditions = patient.get("conditions", [])
                if not conditions:
                    # Neutral - can't evaluate with no data
                    # Changed to False (neutral should not qualify)
                    return False,criterion_type,field,operator,value,"No Conditions Found"
                
                identifier = criterion.get("identifier", [])
                search_term = " ".join([str(x).lower() for x in identifier]) if identifier else str(value).lower()
                logger.info(f"[DEBUG] Search Term: {search_term}")
                for cond in conditions:
                    if isinstance(cond, dict):
                        # Check "description" column in MS3's conditions table
                        description = cond.get("description", "").lower()
                        code = cond.get("code", "").lower()

                        # also check both description and code
                        if search_term in description or search_term in code:
                            logger.debug(f"[MATCH] Found '{search_term}' in condition: {description}")
                            return True,criterion_type,field,operator,value,str(cond)
                    else:
                        # Fallback for string conditions
                        cond_str = str(cond).lower()
                        if search_term in cond_str:
                            return True,criterion_type,field,operator,value,str(cond)

                return False,criterion_type,field,operator,value,"NA"
            
            # Other criterion types - neutral (can't evaluate)
            else:
                # Changed to False (neutral should not qualify)
                logger.info(
                    f"[CRITERION] Match Error 2: field {field} operator {operator} value {value}")

                return False,criterion_type,field,operator,value,"NA"
        
        except Exception as e:

            logger.debug(f"[CRITERION] MATCH Error: {e}")
            # Changed to False (neutral should not qualify)
            return False,"CRITERION MATCH ERROR","-","-","-","-"  # Neutral on error

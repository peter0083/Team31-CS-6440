# init_postgres.py - FIXED data loader with proper FHIR extraction and type hints

import glob
import json
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import psycopg2

from src.ms3.ms3_config import settings


class InitializationState:
    def __init__(self) -> None:
        self.is_initialized: bool = False
        self.is_loading: bool = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None
        self.total_files: int = 0
        self.files_processed: int = 0
        self.patients_loaded: int = 0
        self.conditions_loaded: int = 0
        self.observations_loaded: int = 0
        self.medications_loaded: int = 0
        self.lock: threading.Lock = threading.Lock()
    
    def to_dict(self) -> Dict[str, Any]:
        with self.lock:
            elapsed: Optional[float] = None
            if self.start_time:
                end: float = self.end_time or time.time()
                elapsed = round(end - self.start_time, 2)
            
            return {
                "is_initialized": self.is_initialized,
                "is_loading": self.is_loading,
                "error": self.error,
                "elapsed_seconds": elapsed,
                "progress": {
                    "files_processed": self.files_processed,
                    "total_files": self.total_files,
                    "patients": self.patients_loaded,
                    "conditions": self.conditions_loaded,
                    "observations": self.observations_loaded,
                    "medications": self.medications_loaded,
                },
                "total_records": (
                    self.patients_loaded + self.conditions_loaded +
                    self.observations_loaded + self.medications_loaded
                ),
            }


_state: InitializationState = InitializationState()


def get_db_connection() -> psycopg2.extensions.connection:
    # use psycopg2 instead of SQLalchemy for direct connection
    return psycopg2.connect(
        host="postgres_ms3",
        port=5432,
        database="ms3_db",
        user="postgres",
        password="postgres"
    )


def calculate_age(birth_date_str: Optional[str]) -> Optional[int]:
    try:
        if not birth_date_str:
            return None
        birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = datetime.today().date()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age if age >= 0 else None
    except Exception:
        return None


def extract_race(resource: Dict[str, Any]) -> Optional[str]:
    try:
        for ext in resource.get("extension", []):
            if "us-core-race" in ext.get("url", ""):
                for sub_ext in ext.get("extension", []):
                    if sub_ext.get("url") == "text":
                        return sub_ext.get("valueString")
    except Exception:
        pass
    return None


def extract_ethnicity(resource: Dict[str, Any]) -> Optional[str]:
    try:
        for ext in resource.get("extension", []):
            if "us-core-ethnicity" in ext.get("url", ""):
                for sub_ext in ext.get("extension", []):
                    if sub_ext.get("url") == "text":
                        return sub_ext.get("valueString")
    except Exception:
        pass
    return None


async def load_postgres_data() -> None:
    try:
        with _state.lock:
            _state.is_loading = True
            _state.start_time = time.time()
        
        print("\n" + "="*60)
        print("[INIT] Starting PostgreSQL data loading (psycopg2)")
        print(f"[INIT] FHIR file pattern: {settings.SYNTHEA_FHIR_GLOB}")
        print("="*60)
        
        fhir_files = glob.glob(settings.SYNTHEA_FHIR_GLOB)
        with _state.lock:
            _state.total_files = len(fhir_files)
        print(f"[INIT] Found {len(fhir_files)} FHIR bundle files")
        
        if not fhir_files:
            print("[INIT] No files found!")
            with _state.lock:
                _state.is_initialized = True
                _state.is_loading = False
                _state.end_time = time.time()
            return
        
        # Get connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for i, fhir_file in enumerate(fhir_files):
            try:
                with open(fhir_file, 'r', encoding='utf-8') as f:
                    bundle = json.load(f)
                    _process_bundle(cursor, bundle)
            except Exception as e:
                print(f"[INIT] Error processing {fhir_file}: {e}")
            
            with _state.lock:
                _state.files_processed = i + 1
            
            if (i + 1) % 100 == 0:
                print(f"[INIT] Progress: {i + 1}/{len(fhir_files)} files")
                conn.commit()  # Commit every 100 files
        
        conn.commit()
        cursor.close()
        conn.close()
        
        with _state.lock:
            _state.is_initialized = True
            _state.is_loading = False
            _state.end_time = time.time()
        
        elapsed = _state.end_time - _state.start_time
        print("="*60)
        print(f"[INIT] ✓ Data loading COMPLETE in {elapsed:.2f}s")
        print(f"[INIT] Patients: {_state.patients_loaded}")
        print(f"[INIT] Conditions: {_state.conditions_loaded}")
        print(f"[INIT] Observations: {_state.observations_loaded}")
        print(f"[INIT] Medications: {_state.medications_loaded}")
        print(f"[INIT] Total: {_state.patients_loaded + _state.conditions_loaded + _state.observations_loaded + _state.medications_loaded} records")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n[INIT] ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        with _state.lock:
            _state.error = str(e)
            _state.is_loading = False


def _process_bundle(cursor: psycopg2.extensions.cursor, bundle: Dict[str, Any]) -> None:
    for entry in bundle.get("entry", []):
        resource: Dict[str, Any] = entry.get("resource", {})
        resource_type: str = resource.get("resourceType", "")
        
        if resource_type == "Patient":
            _insert_patient(cursor, resource)
        elif resource_type == "Condition":
            _insert_condition(cursor, resource)
        elif resource_type == "Observation":
            _insert_observation(cursor, resource)
        elif resource_type == "MedicationRequest":
            _insert_medication(cursor, resource)


def _insert_patient(cursor: psycopg2.extensions.cursor, resource: Dict[str, Any]) -> None:
    try:
        patient_id: Optional[str] = resource.get("id")
        if not patient_id:
            return
        
        birth_date: Optional[str] = resource.get("birthDate")
        age: Optional[int] = calculate_age(birth_date)
        gender: Optional[str] = resource.get("gender")
        race: Optional[str] = extract_race(resource)
        ethnicity: Optional[str] = extract_ethnicity(resource)
        
        marital_status: Optional[str] = None
        if resource.get("maritalStatus", {}).get("coding"):
            marital_status = resource["maritalStatus"]["coding"][0].get("display")
        
        city: Optional[str] = None
        if resource.get("address"):
            city = resource["address"][0].get("city")
        
        state: Optional[str] = None
        if resource.get("address"):
            state = resource["address"][0].get("state")
        
        country: Optional[str] = None
        if resource.get("address"):
            country = resource["address"][0].get("country")
        
        sql = """
            INSERT INTO patient (id, birth_date, age, gender, race, ethnicity, marital_status, city, state, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.execute(sql, (
            patient_id,
            birth_date,
            age,
            gender,
            race,
            ethnicity,
            marital_status,
            city,
            state,
            country,
        ))
        
        with _state.lock:
            _state.patients_loaded += 1
        
    except Exception as e:
        print(f"[ERROR] Patient insert failed: {e}")


def _insert_condition(cursor: psycopg2.extensions.cursor, resource: Dict[str, Any]) -> None:
    try:
        condition_id: Optional[str] = resource.get("id")
        if not condition_id:
            return
        
        subject_id: str = resource.get("subject", {}).get("reference", "").split("/")[-1]
        if not subject_id:
            return
        
        coding: Dict[str, Any] = resource.get("code", {}).get("coding", [{}])[0]
        code: Optional[str] = coding.get("code")
        code_system: Optional[str] = coding.get("system")
        description: Optional[str] = resource.get("code", {}).get("text")
        onset_date_time: Optional[str] = resource.get("onsetDateTime")
        clinical_status: Optional[str] = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
        
        sql = """
            INSERT INTO condition (id, subject_id, code, code_system, description, onset_date_time, clinical_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.execute(sql, (
            condition_id,
            subject_id,
            code,
            code_system,
            description,
            onset_date_time,
            clinical_status,
        ))
        
        with _state.lock:
            _state.conditions_loaded += 1
        
    except Exception as e:
        print(f"[ERROR] Condition insert failed: {e}")


def _insert_observation(cursor: psycopg2.extensions.cursor, resource: Dict[str, Any]) -> None:
    try:
        obs_id: Optional[str] = resource.get("id")
        if not obs_id:
            return
        
        subject_id: str = resource.get("subject", {}).get("reference", "").split("/")[-1]
        if not subject_id:
            return
        
        coding: Dict[str, Any] = resource.get("code", {}).get("coding", [{}])[0]
        code: Optional[str] = coding.get("code")
        code_system: Optional[str] = coding.get("system")
        display: Optional[str] = coding.get("display")
        
        value_quantity: Dict[str, Any] = resource.get("valueQuantity", {})
        value: Optional[float] = value_quantity.get("value")
        unit: Optional[str] = value_quantity.get("unit")
        
        effective_date_time: Optional[str] = resource.get("effectiveDateTime")
        reference_range_text: Optional[str] = resource.get("referenceRange", [{}])[0].get("text") if resource.get("referenceRange") else None
        status: Optional[str] = resource.get("status")
        
        sql = """
            INSERT INTO observation (id, subject_id, code, code_system, display, value_quantity_value, value_quantity_unit, effective_date_time, reference_range_text, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.execute(sql, (
            obs_id,
            subject_id,
            code,
            code_system,
            display,
            value,
            unit,
            effective_date_time,
            reference_range_text,
            status,
        ))
        
        with _state.lock:
            _state.observations_loaded += 1
        
    except Exception as e:
        print(f"[ERROR] Observation insert failed: {e}")


def _insert_medication(cursor: psycopg2.extensions.cursor, resource: Dict[str, Any]) -> None:
    try:
        med_id: Optional[str] = resource.get("id")
        if not med_id:
            return
        
        subject_id: str = resource.get("subject", {}).get("reference", "").split("/")[-1]
        if not subject_id:
            return
        
        # Handle both medicationCodeableConcept and medicationReference
        medication_text: Optional[str] = resource.get("medicationCodeableConcept", {}).get("text")
        if not medication_text and resource.get("medicationReference"):
            medication_text = resource.get("medicationReference", {}).get("display")
        
        medication_coding: Dict[str, Any] = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
        generic_name: Optional[str] = medication_coding.get("display")
        
        dosage: Dict[str, Any] = resource.get("dosageInstruction", [{}])[0]
        dose_text: Optional[str] = dosage.get("text")
        frequency_text: Optional[str] = dosage.get("timing", {}).get("repeat", {}).get("frequencyMax")
        
        authored_on: Optional[str] = resource.get("authoredOn")
        status: Optional[str] = resource.get("status")
        
        sql = """
            INSERT INTO medicationrequest (id, subject_id, medication_text, generic_name, dose_text, frequency_text, authored_on, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """
        
        cursor.execute(sql, (
            med_id,
            subject_id,
            medication_text,
            generic_name,
            dose_text,
            frequency_text,
            authored_on,
            status,
        ))
        
        with _state.lock:
            _state.medications_loaded += 1
        
    except Exception as e:
        print(f"[ERROR] Medication insert failed: {e}")


def get_init_status() -> Dict[str, Any]:
    return _state.to_dict()

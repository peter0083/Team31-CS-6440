# init_duckdb_async.py - Async DuckDB Initialization with Progress Tracking
"""
Async background loader for Synthea FHIR JSON data into DuckDB.
- Starts loading in background instead of blocking
- Service starts immediately (handlers check if ready)
- Real-time progress tracking
- Status endpoint to monitor initialization
"""

import glob
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

import duckdb

# =========================================================
# Global State for Progress Tracking
# =========================================================

class InitializationState:
    """Tracks initialization progress."""
    
    def __init__(self):
        self.is_initialized = False
        self.is_loading = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None
        self.total_files = 0
        self.files_processed = 0
        self.patients_loaded = 0
        self.conditions_loaded = 0
        self.observations_loaded = 0
        self.medications_loaded = 0
        self.lock = threading.Lock()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for API response."""
        with self.lock:
            elapsed = None
            if self.start_time:
                end = self.end_time or time.time()
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
                    self.patients_loaded +
                    self.conditions_loaded +
                    self.observations_loaded +
                    self.medications_loaded
                )
            }


# Global state instance
_state = InitializationState()


def get_initialization_status() -> Dict[str, Any]:
    """Get current initialization status."""
    return _state.to_dict()


# =========================================================
# Async Initialization (runs in background thread)
# =========================================================

def _create_tables(conn: duckdb.DuckDBPyConnection) -> None:
    """Create normalized tables for Synthea FHIR data."""
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patient (
            id VARCHAR PRIMARY KEY,
            birthDate DATE,
            gender VARCHAR,
            race VARCHAR,
            ethnicity VARCHAR,
            maritalStatus VARCHAR,
            city VARCHAR,
            state VARCHAR,
            country VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS condition (
            id VARCHAR PRIMARY KEY,
            subject_id VARCHAR,
            code VARCHAR,
            codeSystem VARCHAR,
            description VARCHAR,
            onsetDateTime TIMESTAMP,
            clinicalStatus VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS observation (
            id VARCHAR PRIMARY KEY,
            subject_id VARCHAR,
            code VARCHAR,
            codeSystem VARCHAR,
            display VARCHAR,
            valueQuantity_value DOUBLE,
            valueQuantity_unit VARCHAR,
            effectiveDateTime TIMESTAMP,
            referenceRange_text VARCHAR,
            status VARCHAR
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicationrequest (
            id VARCHAR PRIMARY KEY,
            subject_id VARCHAR,
            medication_text VARCHAR,
            generic_name VARCHAR,
            dose_text VARCHAR,
            frequency_text VARCHAR,
            authoredOn TIMESTAMP,
            status VARCHAR
        )
    """)


def _extract_bundle_resources(
    bundle: Dict[str, Any],
    patients: List[Dict],
    conditions: List[Dict],
    observations: List[Dict],
    medication_requests: List[Dict]
) -> None:
    """Extract resources from a FHIR Bundle."""
    
    entries = bundle.get("entry", [])
    
    for entry in entries:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")
        
        if resource_type == "Patient":
            patients.append(_extract_patient(resource))
        elif resource_type == "Condition":
            conditions.append(_extract_condition(resource))
        elif resource_type == "Observation":
            observations.append(_extract_observation(resource))
        elif resource_type == "MedicationRequest":
            medication_requests.append(_extract_medication_request(resource))


def _extract_patient(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Extract patient data from FHIR Patient resource."""
    
    race = None
    ethnicity = None
    extensions = resource.get("extension", [])
    for ext in extensions:
        url = ext.get("url", "")
        if "us-core-race" in url:
            race_exts = ext.get("extension", [])
            for race_ext in race_exts:
                if race_ext.get("url") == "text":
                    race = race_ext.get("valueString")
        elif "us-core-ethnicity" in url:
            eth_exts = ext.get("extension", [])
            for eth_ext in eth_exts:
                if eth_ext.get("url") == "text":
                    ethnicity = eth_ext.get("valueString")
    
    addresses = resource.get("address", [])
    address = addresses[0] if addresses else {}
    
    return {
        "id": resource.get("id"),
        "birthDate": resource.get("birthDate"),
        "gender": resource.get("gender"),
        "race": race,
        "ethnicity": ethnicity,
        "maritalStatus": resource.get("maritalStatus", {}).get("text"),
        "city": address.get("city"),
        "state": address.get("state"),
        "country": address.get("country")
    }


def _extract_condition(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Extract condition data from FHIR Condition resource."""
    
    subject_ref = resource.get("subject", {}).get("reference", "")
    subject_id = subject_ref.split("/")[-1] if "/" in subject_ref else subject_ref
    
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [])
    coding = codings[0] if codings else {}
    
    return {
        "id": resource.get("id"),
        "subject_id": subject_id,
        "code": coding.get("code"),
        "codeSystem": coding.get("system"),
        "description": code_obj.get("text") or coding.get("display"),
        "onsetDateTime": resource.get("onsetDateTime"),
        "clinicalStatus": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
    }


def _extract_observation(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Extract observation data from FHIR Observation resource."""
    
    subject_ref = resource.get("subject", {}).get("reference", "")
    subject_id = subject_ref.split("/")[-1] if "/" in subject_ref else subject_ref
    
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [])
    coding = codings[0] if codings else {}
    
    value_quantity = resource.get("valueQuantity", {})
    
    ref_ranges = resource.get("referenceRange", [])
    ref_range_text = None
    if ref_ranges:
        ref_range = ref_ranges[0]
        low = ref_range.get("low", {}).get("value")
        high = ref_range.get("high", {}).get("value")
        if low is not None and high is not None:
            ref_range_text = f"{low}-{high}"
    
    return {
        "id": resource.get("id"),
        "subject_id": subject_id,
        "code": coding.get("code"),
        "codeSystem": coding.get("system"),
        "display": code_obj.get("text") or coding.get("display"),
        "valueQuantity_value": value_quantity.get("value"),
        "valueQuantity_unit": value_quantity.get("unit"),
        "effectiveDateTime": resource.get("effectiveDateTime"),
        "referenceRange_text": ref_range_text,
        "status": resource.get("status")
    }


def _extract_medication_request(resource: Dict[str, Any]) -> Dict[str, Any]:
    """Extract medication request data from FHIR MedicationRequest resource."""
    
    subject_ref = resource.get("subject", {}).get("reference", "")
    subject_id = subject_ref.split("/")[-1] if "/" in subject_ref else subject_ref
    
    medication = resource.get("medicationCodeableConcept", {})
    med_codings = medication.get("coding", [])
    med_coding = med_codings[0] if med_codings else {}
    
    dosage_instructions = resource.get("dosageInstruction", [])
    dosage = dosage_instructions[0] if dosage_instructions else {}
    
    dose_text = dosage.get("text")
    timing = dosage.get("timing", {})
    frequency_text = timing.get("code", {}).get("text")
    
    return {
        "id": resource.get("id"),
        "subject_id": subject_id,
        "medication_text": medication.get("text") or med_coding.get("display"),
        "generic_name": None,
        "dose_text": dose_text,
        "frequency_text": frequency_text,
        "authoredOn": resource.get("authoredOn"),
        "status": resource.get("status")
    }


def _insert_patients(conn: duckdb.DuckDBPyConnection, patients: List[Dict]) -> None:
    """Insert patient records into DuckDB."""
    if not patients:
        return
    
    conn.executemany("""
        INSERT OR IGNORE INTO patient 
        (id, birthDate, gender, race, ethnicity, maritalStatus, city, state, country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (p.get("id"), p.get("birthDate"), p.get("gender"), p.get("race"),
         p.get("ethnicity"), p.get("maritalStatus"), p.get("city"),
         p.get("state"), p.get("country"))
        for p in patients
    ])
    
    with _state.lock:
        _state.patients_loaded += len(patients)


def _insert_conditions(conn: duckdb.DuckDBPyConnection, conditions: List[Dict]) -> None:
    """Insert condition records into DuckDB."""
    if not conditions:
        return
    
    conn.executemany("""
        INSERT OR IGNORE INTO condition 
        (id, subject_id, code, codeSystem, description, onsetDateTime, clinicalStatus)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        (c.get("id"), c.get("subject_id"), c.get("code"), c.get("codeSystem"),
         c.get("description"), c.get("onsetDateTime"), c.get("clinicalStatus"))
        for c in conditions
    ])
    
    with _state.lock:
        _state.conditions_loaded += len(conditions)


def _insert_observations(conn: duckdb.DuckDBPyConnection, observations: List[Dict]) -> None:
    """Insert observation records into DuckDB."""
    if not observations:
        return
    
    conn.executemany("""
        INSERT OR IGNORE INTO observation 
        (id, subject_id, code, codeSystem, display, valueQuantity_value, 
         valueQuantity_unit, effectiveDateTime, referenceRange_text, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (o.get("id"), o.get("subject_id"), o.get("code"), o.get("codeSystem"),
         o.get("display"), o.get("valueQuantity_value"), o.get("valueQuantity_unit"),
         o.get("effectiveDateTime"), o.get("referenceRange_text"), o.get("status"))
        for o in observations
    ])
    
    with _state.lock:
        _state.observations_loaded += len(observations)


def _insert_medication_requests(
    conn: duckdb.DuckDBPyConnection,
    medication_requests: List[Dict]
) -> None:
    """Insert medication request records into DuckDB."""
    if not medication_requests:
        return
    
    conn.executemany("""
        INSERT OR IGNORE INTO medicationrequest 
        (id, subject_id, medication_text, generic_name, dose_text, 
         frequency_text, authoredOn, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        (m.get("id"), m.get("subject_id"), m.get("medication_text"),
         m.get("generic_name"), m.get("dose_text"), m.get("frequency_text"),
         m.get("authoredOn"), m.get("status"))
        for m in medication_requests
    ])
    
    with _state.lock:
        _state.medications_loaded += len(medication_requests)


def _load_duckdb_background(
    duckdb_file: str,
    synthea_fhir_glob: str,
    force_reload: bool
) -> None:
    """Background thread function to load DuckDB."""
    
    try:
        with _state.lock:
            _state.is_loading = True
            _state.start_time = time.time()
        
        print("[INIT] Starting background DuckDB initialization")
        print(f"[INIT] Database: {duckdb_file}")
        print(f"[INIT] FHIR files: {synthea_fhir_glob}")
        
        # Ensure parent directory exists
        db_dir = os.path.dirname(duckdb_file)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Connect to DuckDB
        conn = duckdb.connect(duckdb_file, read_only=False)
        
        # Check if tables already exist
        tables_exist = False
        try:
            result = conn.execute("SELECT COUNT(*) FROM patient LIMIT 1").fetchone()
            if result and result[0] >= 0:
                tables_exist = True
                print("[INIT] Tables already exist")
        except Exception:
            tables_exist = False

        if tables_exist and not force_reload:
            print("[INIT] Tables already populated. Skipping initialization.")

            # Query existing counts from database
            try:
                patient_count = conn.execute("SELECT COUNT(*) FROM patient").fetchone()
                condition_count = conn.execute("SELECT COUNT(*) FROM condition").fetchone()
                observation_count = conn.execute("SELECT COUNT(*) FROM observation").fetchone()
                medreq_count = conn.execute("SELECT COUNT(*) FROM medicationrequest").fetchone()

                with _state.lock:
                    _state.patients_loaded = patient_count
                    _state.conditions_loaded = condition_count
                    _state.observations_loaded = observation_count
                    _state.medications_loaded = medreq_count
                    _state.is_initialized = True
                    _state.is_loading = False
                    _state.end_time = time.time()

                print("[INIT] Loaded existing data counts:")
                print(f"       Patients: {patient_count}")
                print(f"       Conditions: {condition_count}")
                print(f"       Observations: {observation_count}")
                print(f"       Medications: {medreq_count}")
            except Exception as e:
                print(f"[INIT] Error querying existing data: {e}")
                with _state.lock:
                    _state.is_initialized = True
                    _state.is_loading = False
                    _state.end_time = time.time()

            conn.close()
            return

            # Drop existing tables if forcing reload
        if force_reload:
            print("[INIT] Dropping existing tables...")
            for table in ["patient", "condition", "observation", "medicationrequest"]:
                try:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
                except Exception:
                    pass
        
        # Create tables
        print("[INIT] Creating tables...")
        _create_tables(conn)
        
        # Find all FHIR bundle files
        fhir_files = glob.glob(synthea_fhir_glob)
        with _state.lock:
            _state.total_files = len(fhir_files)
        
        print(f"[INIT] Found {len(fhir_files)} FHIR bundle files")
        
        if not fhir_files:
            print(f"[INIT] WARNING: No files found matching pattern: {synthea_fhir_glob}")
            with _state.lock:
                _state.is_initialized = True
                _state.is_loading = False
                _state.end_time = time.time()
            conn.close()
            return
        
        # Extract and load data
        patients = []
        conditions = []
        observations = []
        medication_requests = []
        
        batch_size = 10  # Batch files for efficiency
        
        for i, fhir_file in enumerate(fhir_files):
            try:
                with open(fhir_file, 'r', encoding='utf-8') as f:
                    bundle = json.load(f)
                
                _extract_bundle_resources(
                    bundle, patients, conditions, observations, medication_requests
                )
                
            except Exception as e:
                print(f"[INIT] Error processing {fhir_file}: {e}")
                continue
            finally:
                with _state.lock:
                    _state.files_processed = i + 1
                
                # Log progress every N files
                if (i + 1) % 100 == 0:
                    status = _state.to_dict()
                    print(f"[INIT] Progress: {status['progress']['files_processed']}/{status['progress']['total_files']} files")
                    print(f"       Patients: {status['progress']['patients']}, "
                          f"Conditions: {status['progress']['conditions']}, "
                          f"Observations: {status['progress']['observations']}, "
                          f"Medications: {status['progress']['medications']}")
                
                # Batch insert periodically to avoid memory bloat
                if (i + 1) % batch_size == 0:
                    print(f"[INIT] Batch inserting {len(patients)} patients...")
                    _insert_patients(conn, patients)
                    _insert_conditions(conn, conditions)
                    _insert_observations(conn, observations)
                    _insert_medication_requests(conn, medication_requests)
                    patients = []
                    conditions = []
                    observations = []
                    medication_requests = []
        
        # Insert remaining data
        print(f"[INIT] Final insert: {len(patients)} patients...")
        _insert_patients(conn, patients)
        _insert_conditions(conn, conditions)
        _insert_observations(conn, observations)
        _insert_medication_requests(conn, medication_requests)
        
        # Verify data
        patient_count = conn.execute("SELECT COUNT(*) FROM patient").fetchone()[0]
        condition_count = conn.execute("SELECT COUNT(*) FROM condition").fetchone()[0]
        observation_count = conn.execute("SELECT COUNT(*) FROM observation").fetchone()[0]
        medreq_count = conn.execute("SELECT COUNT(*) FROM medicationrequest").fetchone()[0]
        
        print("[INIT] Data loaded successfully:")
        print(f"       patient: {patient_count} rows")
        print(f"       condition: {condition_count} rows")
        print(f"       observation: {observation_count} rows")
        print(f"       medicationrequest: {medreq_count} rows")
        
        conn.close()
        
        with _state.lock:
            _state.is_initialized = True
            _state.is_loading = False
            _state.end_time = time.time()
        
        print(f"[INIT] DuckDB initialization complete! ({_state.end_time - _state.start_time:.2f}s)")
        
    except Exception as e:
        print(f"[INIT] ERROR during initialization: {e}")
        import traceback
        traceback.print_exc()
        with _state.lock:
            _state.error = str(e)
            _state.is_loading = False


def start_async_initialization(
    duckdb_file: str,
    synthea_fhir_glob: str,
    force_reload: bool = False
) -> None:
    """
    Start background DuckDB initialization in a daemon thread.
    Returns immediately - service can start while loading continues.
    """
    print("[INIT] Launching background initialization thread...")
    
    thread = threading.Thread(
        target=_load_duckdb_background,
        args=(duckdb_file, synthea_fhir_glob, force_reload),
        daemon=True
    )
    thread.start()
    print("[INIT] Background thread started. Service can now start immediately!")


if __name__ == "__main__":
    import sys
    
    duckdb_file = sys.argv[1] if len(sys.argv) > 1 else "/data/ms3/ms3.duckdb"
    fhir_glob = sys.argv[2] if len(sys.argv) > 2 else "/data/ms3/synthea/*.json"
    force_reload = os.getenv("FORCE_RELOAD", "0") == "1"
    
    # Start async loading
    start_async_initialization(duckdb_file, fhir_glob, force_reload)
    
    # For testing: wait and check status
    print("\nMonitoring initialization progress...")
    for _ in range(300):  # 5 minutes max
        status = get_initialization_status()
        print(f"Status: {json.dumps(status, indent=2)}")
        if status["is_initialized"]:
            print("Initialization complete!")
            break
        time.sleep(2)

# main.py - Updated to use async DuckDB initialization

from __future__ import annotations

import glob
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

# Import async initialization module
import init_duckdb_async
import pandas as pd
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from schemas import Condition as ConditionItem
from schemas import DataCompleteness, Demographics, LabResult, Medication, Phenotype

# --- Optional imports (loaded lazily) ---
_DUCKDB_AVAILABLE = False
try:
    import duckdb
    _DUCKDB_AVAILABLE = True
except Exception:
    pass

_HIVE_AVAILABLE = False
try:
    from pyhive import hive
    _HIVE_AVAILABLE = True
except Exception:
    pass

# === Config (env-driven with safe defaults) ===

USE_DUCKDB = os.getenv("USE_DUCKDB", "1") == "1"
DUCKDB_FILE = os.getenv("DUCKDB_FILE")
DWH_PATH = os.getenv("DWH_PATH")
PATIENT_GLOB = os.getenv("DWH_PATIENT_GLOB") or (f"{DWH_PATH}/patient/*.parquet" if DWH_PATH else None)
CONDITION_GLOB = os.getenv("DWH_CONDITION_GLOB") or (f"{DWH_PATH}/condition/*.parquet" if DWH_PATH else None)
OBSERVATION_GLOB = os.getenv("DWH_OBSERVATION_GLOB") or (f"{DWH_PATH}/observation/*.parquet" if DWH_PATH else None)
MEDREQ_GLOB = os.getenv("DWH_MEDREQ_GLOB") or (f"{DWH_PATH}/medicationrequest/*.parquet" if DWH_PATH else None)

HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10000"))
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "hive")
HIVE_DATABASE = os.getenv("HIVE_DATABASE", "default")

TBL_PATIENT = os.getenv("TBL_PATIENT", "patient")
TBL_CONDITION = os.getenv("TBL_CONDITION", "condition")
TBL_OBSERVATION = os.getenv("TBL_OBSERVATION", "observation")
TBL_MEDREQ = os.getenv("TBL_MEDREQ", "medicationrequest")

CORS_ALLOW_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]

# =========================================================
# Database access helpers
# =========================================================

_duckdb_conn = None
_hive_conn = None
_initialized_views = False


def _get_duckdb() -> "duckdb.DuckDBPyConnection":
    """Return a DuckDB connection (create if missing)."""
    global _duckdb_conn, _initialized_views
    if not _DUCKDB_AVAILABLE:
        raise RuntimeError("duckdb not installed; set USE_DUCKDB=0 or install duckdb")
    if _duckdb_conn is None:
        if DUCKDB_FILE:
            _duckdb_conn = duckdb.connect(DUCKDB_FILE, read_only=False)
        else:
            _duckdb_conn = duckdb.connect(":memory:")
            if not DUCKDB_FILE:
                view_specs = [
                    (TBL_PATIENT, PATIENT_GLOB),
                    (TBL_CONDITION, CONDITION_GLOB),
                    (TBL_OBSERVATION, OBSERVATION_GLOB),
                    (TBL_MEDREQ, MEDREQ_GLOB),
                ]
                for logical, glob_path in view_specs:
                    if not glob_path:
                        continue
                    matches = glob.glob(glob_path)
                    if not matches:
                        continue
                    _duckdb_conn.execute(
                        f"CREATE OR REPLACE VIEW {logical} AS SELECT * FROM read_parquet('{glob_path}')"
                    )
            _initialized_views = True
    return _duckdb_conn


def _get_hive() -> Any:
    """Return a Hive/Thrift connection (create if missing)."""
    global _hive_conn
    if not _HIVE_AVAILABLE:
        raise RuntimeError("pyhive not installed; set USE_DUCKDB=1 or install pyhive/thrift")
    if _hive_conn is None:
        _hive_conn = hive.Connection(
            host=HIVE_HOST,
            port=HIVE_PORT,
            username=HIVE_USERNAME,
            database=HIVE_DATABASE,
            auth="NOSASL",
        )
    return _hive_conn


def q(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """Execute query and return DataFrame."""
    if USE_DUCKDB:
        con = _get_duckdb()
        df = con.execute(sql, params or {}).fetch_df()
        return cast(pd.DataFrame, df)
    con = _get_hive()
    cur = con.cursor()
    bound_sql = sql
    if params:
        def _escape(v: Any) -> str:
            if v is None:
                return "NULL"
            if isinstance(v, (int, float)):
                return str(v)
            return "'" + str(v).replace("'", "''") + "'"
        for k, v in params.items():
            bound_sql = bound_sql.replace(f":{k}", _escape(v))
    cur.execute(bound_sql)
    cols = [c[0] for c in (cur.description or [])]
    rows = cur.fetchall() if cur.description else []
    df = pd.DataFrame(rows, columns=cols)
    return cast(pd.DataFrame, df)


# =========================================================
# ✓ LIFESPAN HANDLER - STARTS ASYNC INITIALIZATION
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler.
    Starts async background DuckDB initialization.
    Service starts immediately while loading continues.
    """
    # Startup
    print("[STARTUP] MS3 Service starting up...")
    
    if USE_DUCKDB and DUCKDB_FILE:
        synthea_fhir_glob = os.getenv("SYNTHEA_FHIR_GLOB", "/data/ms3/synthea/*.json")
        force_reload = os.getenv("FORCE_RELOAD", "0") == "1"
        
        # Start background initialization (non-blocking)
        init_duckdb_async.start_async_initialization(
            duckdb_file=DUCKDB_FILE,
            synthea_fhir_glob=synthea_fhir_glob,
            force_reload=force_reload
        )
        print("[STARTUP] Background initialization started. Service is now ready!")
    else:
        print("[STARTUP] DuckDB async initialization skipped (USE_DUCKDB=0 or no DUCKDB_FILE)")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] MS3 Service shutting down...")
    global _duckdb_conn, _hive_conn
    if _duckdb_conn:
        _duckdb_conn.close()
        _duckdb_conn = None
    if _hive_conn:
        _hive_conn.close()
        _hive_conn = None


# =========================================================
# ✓ APP INITIALIZATION WITH LIFESPAN
# =========================================================

app = FastAPI(
    title="MS3 — Patient Phenotype Builder",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# Health endpoints
# =========================================================

@app.get("/live")
def live() -> Dict[str, str]:
    """Liveness probe - service is running."""
    return {"status": "alive"}


@app.get("/ready")
def ready() -> Dict[str, str]:
    """Readiness probe - service is ready to handle requests."""
    status = init_duckdb_async.get_initialization_status()
    
    # If still initializing but tables exist, we can serve requests
    if not status["is_initialized"]:
        # Check if tables exist in database
        try:
            if USE_DUCKDB:
                _ = _get_duckdb()
            else:
                _ = _get_hive()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Initializing... Error: {str(e)}"
            )
        
        try:
            sql = f"SELECT 1 FROM {TBL_PATIENT} LIMIT 1"
            _ = q(sql)
        except Exception:
            # Tables don't exist yet, but that's ok - still initializing
            raise HTTPException(
                status_code=503,
                detail=f"Initializing... {status['progress']['files_processed']}/{status['progress']['total_files']} files processed"
            )
    
    return {"status": "ready"}


@app.get("/api/ms3/initialization-status")
def initialization_status() -> Dict[str, Any]:
    """
    Get detailed initialization progress.
    Useful for monitoring the background loader.
    """
    return init_duckdb_async.get_initialization_status()


# =========================================================
# Patient endpoints
# =========================================================

@app.get("/api/ms3/patients")
def get_patients(condition: Optional[str] = None) -> Dict[str, Any]:
    """Return a list of patient IDs."""
    # Check if initialization is complete
    status = init_duckdb_async.get_initialization_status()
    if not status["is_initialized"]:
        raise HTTPException(
            status_code=503,
            detail=f"Service initializing... {status['progress']['patients']} patients loaded so far"
        )
    
    try:
        sql_get_patients = f"""
        SELECT DISTINCT p.id as patient_id
        FROM {TBL_PATIENT} p
        LIMIT 100
        """
        df_patients = q(sql_get_patients)

        if condition:
            condition_lower = condition.lower().strip()
            condition_pattern = f"%{condition_lower}%"
            sql_filtered = f"""
            SELECT DISTINCT p.id as patient_id
            FROM {TBL_PATIENT} p
            INNER JOIN {TBL_CONDITION} c 
              ON p.id = CASE 
                WHEN c.subject_id LIKE 'urn:uuid:%' 
                THEN substr(c.subject_id, 10)  -- Extract UUID from 'urn:uuid:...'
                ELSE c.subject_id
              END
            WHERE LOWER(c.description) LIKE '{condition_pattern}'
            OR LOWER(c.code) LIKE '{condition_pattern}'
            LIMIT 100
            """
            df_patients = q(sql_filtered)

        patients = []
        if df_patients is not None and not df_patients.empty:
            for idx, row in df_patients.iterrows():
                patient_id = str(row["patient_id"]).strip()
                patients.append({
                    "patient_id": patient_id,
                    "id": patient_id,
                    "name": None
                })

        return {
            "patients": patients,
            "total": len(patients),
            "condition": condition
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in /api/ms3/patients: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching patients: {str(e)}"
        )


@app.get("/api/ms3/debug/counts")
def debug_counts() -> Dict[str, Any]:
    """Debug endpoint to check record counts."""
    try:
        patient_count = int(q(f"SELECT COUNT(*) as cnt FROM {TBL_PATIENT}").iloc[0]['cnt'])
        condition_count = int(q(f"SELECT COUNT(*) as cnt FROM {TBL_CONDITION}").iloc[0]['cnt'])

        # Try to get a sample condition
        sample_condition = q(f"SELECT * FROM {TBL_CONDITION} LIMIT 1")

        return {
            "patients": patient_count,
            "conditions": condition_count,
            "sample_condition": sample_condition.to_dict('records') if not sample_condition.empty else None
        }
    except Exception as e:
        return {"error": str(e)}


@app.get(
    "/api/ms3/patient-phenotype/{patient_id}",
    response_model=Phenotype,
    response_model_exclude_none=True,
)
def get_patient_phenotype(patient_id: str = Path(..., min_length=1)) -> Phenotype:
    """
    Build a normalized phenotype from FHIR-like tables.
    Assumes Synthea-ish schemas; environment variables allow renaming/mapping.
    """
    
    # Check if initialization is complete
    status = init_duckdb_async.get_initialization_status()
    if not status["is_initialized"]:
        raise HTTPException(
            status_code=503,
            detail=f"Service initializing... {status['progress']['patients']} patients loaded so far"
        )

    # ---------------- Demographics ----------------
    pdf = q(
        f"""
        SELECT *
        FROM {TBL_PATIENT}
        WHERE id = :pid
        LIMIT 1
        """,
        {"pid": patient_id},
    )

    if pdf.empty:
        raise HTTPException(status_code=404, detail=f"patient '{patient_id}' not found")

    prow = pdf.iloc[0].to_dict()

    # birth date → age
    age_val: Optional[int] = None
    birth_raw = _first_present(prow, "birthDate", "birth_date", "dob")
    if birth_raw is not None:
        try:
            dob = pd.to_datetime(birth_raw, utc=True, errors="coerce")
            if pd.notna(dob):
                today = pd.Timestamp.now(tz="UTC").normalize()
                age_val = int((today - dob.normalize()).days // 365.25)
        except Exception:
            age_val = None

    demographics = Demographics(
        age=age_val if age_val is not None else 0,
        gender=_opt_str(_first_present(prow, "gender", "sex")),
        race=_opt_str(_first_present(prow, "race")),
        ethnicity=_opt_str(_first_present(prow, "ethnicity")),
    )

    # ---------------- Conditions ----------------
    cdf = q(
        f"""
        SELECT *
        FROM {TBL_CONDITION}
        WHERE subject_id = :pid
        ORDER BY COALESCE(onsetDateTime, onset_date, '1970-01-01') DESC
        """,
        {"pid": patient_id},
    )

    conditions: List[ConditionItem] = []
    if not cdf.empty:
        for _, r in cdf.iterrows():
            rd = r.to_dict()
            conditions.append(
                ConditionItem(
                    code_system=_opt_str(_first_present(rd, "codeSystem", "code_system", "system")) or "ICD-10",
                    code=_opt_str(_first_present(rd, "code", "icd10", "snomed")) or "",
                    description=_opt_str(_first_present(rd, "description", "display")),
                    onset_date=_opt_str(_first_present(rd, "onsetDateTime", "onset_date")),
                    status=_opt_str(_first_present(rd, "clinicalStatus", "status")),
                )
            )

    # ---------------- Lab results (Observations) ----------------
    odf = q(
        f"""
        SELECT *
        FROM {TBL_OBSERVATION}
        WHERE subject_id = :pid
        ORDER BY COALESCE(effectiveDateTime, effective_date, '1970-01-01') DESC
        """,
        {"pid": patient_id},
    )

    lab_results: List[LabResult] = []
    if not odf.empty:
        tmp = odf.copy()
        # create normalized columns if missing
        if "display" not in tmp.columns:
            tmp["display"] = tmp.get("test", tmp.get("code", ""))
        if "effectiveDateTime" not in tmp.columns:
            tmp["effectiveDateTime"] = tmp.get("effective_date")
        if "valueQuantity_value" not in tmp.columns:
            tmp["valueQuantity_value"] = tmp.get("value")
        if "valueQuantity_unit" not in tmp.columns:
            tmp["valueQuantity_unit"] = tmp.get("unit")
        if "referenceRange_text" not in tmp.columns:
            tmp["referenceRange_text"] = tmp.get("reference_range")

        tmp = tmp.sort_values(by=["display", "effectiveDateTime"], ascending=[True, False])
        latest = tmp.drop_duplicates(subset=["display"], keep="first")

        for _, r in latest.iterrows():
            test_name = _opt_str(r.get("display"))
            value = r.get("valueQuantity_value")
            unit = _opt_str(r.get("valueQuantity_unit"))
            date = _opt_str(r.get("effectiveDateTime"))
            ref = _opt_str(r.get("referenceRange_text"))
            status = _opt_str(r.get("status"))

            lab_results.append(
                LabResult(
                    test=test_name or "",
                    value=float(value) if (value is not None and pd.notna(value)) else None,
                    unit=unit,
                    date=date,
                    reference_range=ref,
                    status=status,
                )
            )

    # ---------------- Medications (MedicationRequest) ----------------
    mdf = q(
        f"""
        SELECT *
        FROM {TBL_MEDREQ}
        WHERE subject_id = :pid
        ORDER BY COALESCE(authoredOn, start_date, '1970-01-01') DESC
        """,
        {"pid": patient_id},
    )

    medications: List[Medication] = []
    if not mdf.empty:
        tmp = mdf.copy()
        if "medication_text" not in tmp.columns:
            tmp["medication_text"] = tmp.get("name", tmp.get("medication"))
        if "generic_name" not in tmp.columns:
            tmp["generic_name"] = tmp.get("generic")
        if "dose_text" not in tmp.columns:
            tmp["dose_text"] = tmp.get("dosage")
        if "frequency_text" not in tmp.columns:
            tmp["frequency_text"] = tmp.get("frequency")
        if "authoredOn" not in tmp.columns:
            tmp["authoredOn"] = tmp.get("start_date")

        for _, r in tmp.iterrows():
            medications.append(
                Medication(
                    name=_opt_str(r.get("medication_text")) or "",
                    generic_name=_opt_str(r.get("generic_name")),
                    dosage=_opt_str(r.get("dose_text")),
                    frequency=_opt_str(r.get("frequency_text")),
                    start_date=_opt_str(r.get("authoredOn")),
                    status=_opt_str(r.get("status")),
                )
            )

    # ---------------- Pregnancy & Smoking (simple baseline) ----------------
    pregnancy_status = "not_pregnant"
    smoking_status = "never_smoker"

    # ---------------- Data completeness ----------------
    missing_fields: List[str] = []

    demo_score = 1.0
    for key in ("age", "gender", "race", "ethnicity"):
        if getattr(demographics, key) in (None, "", 0) and key != "age":
            demo_score -= 0.25
            missing_fields.append(f"demographics.{key}")
        if key == "age" and (demographics.age is None or demographics.age == 0):
            demo_score -= 0.25
            missing_fields.append("demographics.age")

    cond_score = 1.0 if len(conditions) > 0 else 0.5

    labs_score = 0.0
    if len(lab_results) > 0:
        labs_score = 0.5
        if any((lr.test or "").lower().startswith("hba1c") for lr in lab_results):
            labs_score = min(1.0, labs_score + 0.5)

    med_score = 1.0 if len(medications) > 0 else 0.0

    overall = round((demo_score + cond_score + labs_score + med_score) / 4.0, 2)

    completeness = DataCompleteness(
        overall_score=overall,
        demographics_score=round(demo_score, 2),
        conditions_score=round(cond_score, 2),
        labs_score=round(labs_score, 2),
        medications_score=round(med_score, 2),
        missing_fields=missing_fields,
    )

    # ---------------- Build response ----------------
    return Phenotype(
        patient_id=patient_id,
        phenotype_timestamp=_iso_now(),
        demographics=demographics,
        conditions=conditions,
        lab_results=lab_results,
        medications=medications,
        pregnancy_status=pregnancy_status,
        smoking_status=smoking_status,
        data_completeness=completeness,
    )


# =========================================================
# Utilities
# =========================================================

def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _first_present(d: Dict[str, Any], *candidates: str) -> Any:
    """Return the first non-null, present value under the provided candidate keys."""
    for k in candidates:
        if k in d and pd.notna(d[k]):
            return d[k]
    return None

from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware

from schemas import Condition as ConditionItem  # type: ignore
from schemas import DataCompleteness, Demographics, LabResult, Medication, Phenotype

# --- Optional imports (loaded lazily) ---
_DUCKDB_AVAILABLE = False
try:
    import duckdb  # type: ignore
    _DUCKDB_AVAILABLE = True
except Exception:
    pass

_HIVE_AVAILABLE = False
try:
    from pyhive import hive  # type: ignore
    _HIVE_AVAILABLE = True
except Exception:
    pass

# === Config (env-driven with safe defaults) ===
USE_DUCKDB = os.getenv("USE_DUCKDB", "1") == "1"

# If using DuckDB with Parquet, you can either:
#  - Set a DATABASE file (DUCKDB_FILE), OR
#  - Point to Parquet globs per table (DWH_*_GLOB)
DUCKDB_FILE = os.getenv("DUCKDB_FILE")  # e.g., "/data/ms3.duckdb"

# Parquet directory globs (when no DUCKDB_FILE is given)
DWH_PATH = os.getenv("DWH_PATH")  # e.g., "/data/dwh"
PATIENT_GLOB = os.getenv("DWH_PATIENT_GLOB") or (f"{DWH_PATH}/patient/*.parquet" if DWH_PATH else None)
CONDITION_GLOB = os.getenv("DWH_CONDITION_GLOB") or (f"{DWH_PATH}/condition/*.parquet" if DWH_PATH else None)
OBSERVATION_GLOB = os.getenv("DWH_OBSERVATION_GLOB") or (f"{DWH_PATH}/observation/*.parquet" if DWH_PATH else None)
MEDREQ_GLOB = os.getenv("DWH_MEDREQ_GLOB") or (f"{DWH_PATH}/medicationrequest/*.parquet" if DWH_PATH else None)

# Hive/Trino/Thrift (if not using DuckDB)
HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10000"))
HIVE_USERNAME = os.getenv("HIVE_USERNAME", "hive")
HIVE_DATABASE = os.getenv("HIVE_DATABASE", "default")

# Table names (logical)
TBL_PATIENT = os.getenv("TBL_PATIENT", "patient")
TBL_CONDITION = os.getenv("TBL_CONDITION", "condition")
TBL_OBSERVATION = os.getenv("TBL_OBSERVATION", "observation")
TBL_MEDREQ = os.getenv("TBL_MEDREQ", "medicationrequest")

# Allowed CORS origins for the frontend
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
            # In-memory database; we will register Parquet views if globs are provided.
            _duckdb_conn = duckdb.connect(":memory:")

        # Create views over parquet globs if present
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
                # no files yet; skip creating this view
                continue
            _duckdb_conn.execute(
            f"CREATE OR REPLACE VIEW {logical} AS SELECT * FROM read_parquet('{glob_path}')"
            )
        _initialized_views = True


    return _duckdb_conn


def _get_hive():
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
            auth="NOSASL",  # adjust for your env
        )
    return _hive_conn


def q(sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Run a SQL query against DuckDB or Hive and return a pandas DataFrame.
    Named parameter style: use `:name` in SQL; we'll bind accordingly for DuckDB,
    or perform a safe format for Hive (limited to strings/numbers).
    """
    if USE_DUCKDB:
        con = _get_duckdb()
        if params:
            # DuckDB supports Python named parameters via 'execute' with a dict
            res = con.execute(sql, params).fetch_df()
        else:
            res = con.execute(sql).fetch_df()
        return res

    # Hive path
    con = _get_hive()
    cur = con.cursor()

    bound_sql = sql
    if params:
        # Minimal safe parameter binding for Hive (no server-side named params).
        # Only substitute simple literals.
        def _escape(v: Any) -> str:
            if v is None:
                return "NULL"
            if isinstance(v, (int, float)):
                return str(v)
            # naive string escape
            s = str(v).replace("'", "''")
            return f"'{s}'"

        for k, v in params.items():
            bound_sql = bound_sql.replace(f":{k}", _escape(v))

    cur.execute(bound_sql)
    cols = [c[0] for c in cur.description] if cur.description else []
    rows = cur.fetchall() if cur.description else []
    return pd.DataFrame(rows, columns=cols)


# =========================================================
# App
# =========================================================
app = FastAPI(title="MS3 — Patient Phenotype Builder", version="1.0.0")

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
    return {"status": "alive"}


@app.get("/ready")
def ready() -> Dict[str, str]:
    """
    Readiness checks:
    - Can we open a DB connection?
    - If DuckDB without file: if globs exist, views are created.
    - Try a lightweight count on patient table (tolerate empty).
    """
    try:
        if USE_DUCKDB:
            _ = _get_duckdb()
        else:
            _ = _get_hive()
    except Exception as e:
        # Not ready: cannot connect
        raise HTTPException(status_code=503, detail=f"db_not_ready: {e}")

    # Optional sanity query (tolerate zero rows)
    try:
        sql = f"SELECT 1 FROM {TBL_PATIENT} LIMIT 1"
        _ = q(sql)
    except Exception:
        # Patient table might not exist yet; still report not ready
        raise HTTPException(status_code=503, detail="patient_table_missing")

    return {"status": "ready"}


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


# =========================================================
# Contract endpoint
# =========================================================
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

    # ---------------- Demographics ----------------
    # Common Synthea columns: id, birthDate, gender, race, ethnicity
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
    # Common Synthea columns: subject_id, code, codeSystem, description, onsetDateTime, clinicalStatus
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
    # Common Synthea columns:
    #   subject_id, code, display, valueQuantity_value, valueQuantity_unit,
    #   effectiveDateTime, referenceRange_text, status
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
        # normalize names and get latest per 'test' (display)
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
    # Common Synthea columns:
    #   subject_id, medication_text, generic_name, dose_text, frequency_text,
    #   authoredOn, status
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
    # You can refine with specific LOINC/Observation codes later.
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

# main.py - Complete MS3 API with age field

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

import src.ms3.init_postgres as init_postgres
from src.ms3.ms3_database import (
    ConditionDB,
    MedicationRequestDB,
    ObservationDB,
    PatientDB,
    async_session_maker,
    check_db_connection,
    close_db,
    init_db,
)
from src.ms3.schemas import Condition as ConditionItem
from src.ms3.schemas import Demographics, LabResult, Medication, Phenotype

# =========================================================
# LIFESPAN HANDLER
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan - loads all data synchronously during startup."""
    print("\n" + "="*60)
    print("[STARTUP] MS3 Service starting up...")
    print("="*60)
    
    await init_db()
    print("[STARTUP] ✓ Database tables initialized")
    
    is_connected = await check_db_connection()
    if not is_connected:
        print("[STARTUP] ✗ WARNING: Could not connect to database")
    
    print("[STARTUP] Starting synchronous data loading (blocking)...")
    
    try:
        await init_postgres.load_postgres_data()
        print("[STARTUP] ✓ Data loading complete")
    except Exception as e:
        print(f"[STARTUP] ✗ ERROR during data loading: {e}")
        import traceback
        traceback.print_exc()
    
    print("="*60)
    print("[STARTUP] MS3 Service is now READY")
    print("="*60 + "\n")
    
    yield
    
    print("\n[SHUTDOWN] MS3 Service shutting down...")
    await close_db()
    print("[SHUTDOWN] ✓ Database connection closed\n")

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    lifespan=lifespan,
    title="MS3 Microservice",
    version="1.0.0",
    description="Medical Synthetic Surveillance System - PostgreSQL Backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = init_postgres.get_init_status()
    if status["is_loading"]:
        return {"status": "initializing", "message": "Service is loading data"}
    elif status["is_initialized"]:
        return {"status": "healthy", "service": "MS3", "ready": True}
    else:
        return {"status": "ready", "service": "MS3"}

@app.get("/")
async def root():
    """Root endpoint."""
    status = init_postgres.get_init_status()
    return {
        "service": "MS3 Microservice",
        "version": "1.0.0",
        "status": "initializing" if status["is_loading"] else "ready",
        "initialized": status["is_initialized"],
        "docs": "/docs",
    }

# =========================================================
# DB STATUS
# =========================================================

@app.get("/api/ms3/db-status")
async def db_status():
    """Database connection status."""
    is_connected = await check_db_connection()
    return {
        "connected": is_connected,
        "database": "PostgreSQL",
        "initialized": init_postgres.get_init_status()["is_initialized"],
    }

# =========================================================
# INITIALIZATION STATUS
# =========================================================

@app.get("/api/ms3/initialization-status")
async def initialization_status():
    """Data loading status."""
    return init_postgres.get_init_status()

# =========================================================
# STATISTICS
# =========================================================

@app.get("/api/ms3/statistics")
async def get_statistics():
    """Data statistics."""
    async with async_session_maker() as session:
        try:
            patient_count = await session.execute(text("SELECT COUNT(*) FROM patient"))
            condition_count = await session.execute(text("SELECT COUNT(*) FROM condition"))
            observation_count = await session.execute(text("SELECT COUNT(*) FROM observation"))
            medication_count = await session.execute(text("SELECT COUNT(*) FROM medicationrequest"))
            
            pc = patient_count.scalar() or 0
            cc = condition_count.scalar() or 0
            oc = observation_count.scalar() or 0
            mc = medication_count.scalar() or 0
            
            return {
                "patients": pc,
                "conditions": cc,
                "observations": oc,
                "medications": mc,
                "total_records": pc + cc + oc + mc,
            }
        except Exception as e:
            return {"error": str(e), "patients": 0, "conditions": 0, "observations": 0, "medications": 0}

# =========================================================
# PATIENTS LIST
# =========================================================

@app.get("/api/ms3/patients", response_model=List[Demographics])
async def get_patients(limit: int = 100, offset: int = 0):
    """Get all patients."""
    async with async_session_maker() as session:
        query = select(PatientDB).limit(limit).offset(offset)
        result = await session.execute(query)
        patients = result.scalars().all()
        return [
            Demographics(
                patient_id=p.id,
                birth_date=p.birth_date,
                age=p.age,
                gender=p.gender,
                race=p.race,
                ethnicity=p.ethnicity,
            )
            for p in patients
        ]

# =========================================================
# GET SINGLE PATIENT
# =========================================================

@app.get("/api/ms3/patients/{patient_id}", response_model=Demographics)
async def get_patient(patient_id: str):
    """Get patient by ID."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(PatientDB).where(PatientDB.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        return Demographics(
            patient_id=patient.id,
            birth_date=patient.birth_date,
            age=patient.age,
            gender=patient.gender,
            race=patient.race,
            ethnicity=patient.ethnicity,
        )

# =========================================================
# PATIENT CONDITIONS
# =========================================================

@app.get("/api/ms3/patients/{patient_id}/conditions", response_model=List[ConditionItem])
async def get_patient_conditions(patient_id: str):
    """Get conditions for patient."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(ConditionDB).where(ConditionDB.subject_id == patient_id)
        )
        conditions = result.scalars().all()
        return [
            ConditionItem(
                condition_id=c.id,
                code=c.code,
                code_system=c.code_system,
                description=c.description,
                onset_date_time=c.onset_date_time,
                clinical_status=c.clinical_status,
            )
            for c in conditions
        ]

# =========================================================
# PATIENT OBSERVATIONS
# =========================================================

@app.get("/api/ms3/patients/{patient_id}/observations", response_model=List[LabResult])
async def get_patient_observations(patient_id: str):
    """Get observations for patient."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(ObservationDB).where(ObservationDB.subject_id == patient_id)
        )
        observations = result.scalars().all()
        return [
            LabResult(
                observation_id=o.id,
                code=o.code,
                code_system=o.code_system,
                display=o.display,
                value=o.value_quantity_value,
                unit=o.value_quantity_unit,
                effective_date_time=o.effective_date_time,
                reference_range_text=o.reference_range_text,
                status=o.status,
            )
            for o in observations
        ]

# =========================================================
# PATIENT MEDICATIONS
# =========================================================

@app.get("/api/ms3/patients/{patient_id}/medications", response_model=List[Medication])
async def get_patient_medications(patient_id: str):
    """Get medications for patient."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(MedicationRequestDB).where(MedicationRequestDB.subject_id == patient_id)
        )
        medications = result.scalars().all()
        return [
            Medication(
                medication_id=m.id,
                name=m.medication_text,
                generic_name=m.generic_name,
                dose=m.dose_text,
                frequency=m.frequency_text,
                authored_on=m.authored_on,
                status=m.status,
            )
            for m in medications
        ]

# =========================================================
# PATIENT PHENOTYPE (COMPLETE RECORD)
# =========================================================

@app.get("/api/ms3/patients/{patient_id}/phenotype", response_model=Phenotype)
async def get_patient_phenotype(patient_id: str):
    """Get complete phenotype for patient with age included."""
    async with async_session_maker() as session:
        # Get patient
        patient_result = await session.execute(
            select(PatientDB).where(PatientDB.id == patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Get conditions
        conditions_result = await session.execute(
            select(ConditionDB).where(ConditionDB.subject_id == patient_id)
        )
        conditions = conditions_result.scalars().all()
        
        # Get observations
        observations_result = await session.execute(
            select(ObservationDB).where(ObservationDB.subject_id == patient_id)
        )
        observations = observations_result.scalars().all()
        
        # Get medications
        medications_result = await session.execute(
            select(MedicationRequestDB).where(MedicationRequestDB.subject_id == patient_id)
        )
        medications = medications_result.scalars().all()
        
        # Build phenotype with age
        return Phenotype(
            patient_id=patient.id,
            demographics=Demographics(
                patient_id=patient.id,
                birth_date=patient.birth_date,
                age=patient.age,
                gender=patient.gender,
                race=patient.race,
                ethnicity=patient.ethnicity,
            ),
            conditions=[
                ConditionItem(
                    condition_id=c.id,
                    code=c.code,
                    code_system=c.code_system,
                    description=c.description,
                    onset_date_time=c.onset_date_time,
                    clinical_status=c.clinical_status,
                )
                for c in conditions
            ],
            lab_results=[
                LabResult(
                    observation_id=o.id,
                    code=o.code,
                    code_system=o.code_system,
                    display=o.display,
                    value=o.value_quantity_value,
                    unit=o.value_quantity_unit,
                    effective_date_time=o.effective_date_time,
                    reference_range_text=o.reference_range_text,
                    status=o.status,
                )
                for o in observations
            ],
            medications=[
                Medication(
                    medication_id=m.id,
                    name=m.medication_text,
                    generic_name=m.generic_name,
                    dose=m.dose_text,
                    frequency=m.frequency_text,
                    authored_on=m.authored_on,
                    status=m.status,
                )
                for m in medications
            ],
        )

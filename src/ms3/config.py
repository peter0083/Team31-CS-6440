# config.py - MS3 Configuration

import os

# ============================================================================
# Database Configuration
# ============================================================================

# Use DuckDB for fast local queries (recommended for development)
# Set to "0" to use Hive for production big data workloads
USE_DUCKDB = os.getenv("USE_DUCKDB", "1") == "1"

# DuckDB persistence (optional)
# Format: /path/to/database.duckdb or leave empty for in-memory
DUCKDB_FILE = os.getenv("DUCKDB_FILE", "/data/ms3/ms3.duckdb")

# Hive configuration (only used if USE_DUCKDB=0)
HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10001"))
HIVE_DB = os.getenv("HIVE_DB", "default")

# ============================================================================
# Data Path Configuration - Points to Synthea FHIR JSON files
# ============================================================================

# Base data warehouse path
DWH_PATH = os.getenv("DWH_PATH", "/data/ms3/synthea")

# Glob patterns for Synthea FHIR Bundle files
# These JSON files contain Patient, Condition, Observation, MedicationRequest resources
SYNTHEA_FHIR_GLOB = os.getenv("SYNTHEA_FHIR_GLOB", f"{DWH_PATH}/*.json")

# Individual resource globs (optional - if pre-split into separate files)
PATIENT_GLOB = os.getenv("PATIENT_GLOB", f"{DWH_PATH}/patient/*.json")
CONDITION_GLOB = os.getenv("CONDITION_GLOB", f"{DWH_PATH}/condition/*.json")
OBSERVATION_GLOB = os.getenv("OBSERVATION_GLOB", f"{DWH_PATH}/observation/*.json")
MEDREQ_GLOB = os.getenv("MEDREQ_GLOB", f"{DWH_PATH}/medicationrequest/*.json")

# ============================================================================
# API Configuration
# ============================================================================

# CORS origins for MS4 and frontend access
CORS_ALLOW_ORIGINS = os.getenv(
    "CORS_ALLOW_ORIGINS", 
    "http://localhost:3000,http://localhost:5173"
).split(",")

# API port
API_PORT = int(os.getenv("API_PORT", 8003))

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

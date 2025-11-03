# config.py
import os

HIVE_HOST = os.getenv("HIVE_HOST", "localhost")
HIVE_PORT = int(os.getenv("HIVE_PORT", "10001"))
HIVE_DB   = os.getenv("HIVE_DB", "default")

# Optional fallback to DuckDB (read Parquet) when set to "1"
USE_DUCKDB = os.getenv("USE_DUCKDB", "0") == "1"
DWH_PATH   = os.getenv("DWH_PATH", "/opt/dwh")  # mount your fhir-data-pipes dwh here

# CORS origins for MS4 and local dev
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")

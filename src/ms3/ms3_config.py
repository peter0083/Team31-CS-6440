"""Configuration settings for MS3 microservice: patient phenotype builder."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where this config file is located
CONFIG_DIR = Path(__file__).parent


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(CONFIG_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    SERVICE_NAME: str = "MS3 Patient Phenotype Builder"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/ms3_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Data Path Configuration - Points to Synthea FHIR JSON files
    DWH_PATH: str = "/data/ms3/synthea"
    SYNTHEA_FHIR_GLOB: str = "/data/ms3/synthea/*.json"

    # CORS Configuration
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Initialization Configuration
    FORCE_RELOAD: bool = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        raise RuntimeError(f"Failed to load settings: {e}") from e


settings = get_settings()


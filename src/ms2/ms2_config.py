"""Configuration settings for MS2 microservice: clinical trial criteria parser."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the directory where this config file is located
CONFIG_DIR = Path(__file__).parent

class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(CONFIG_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    SERVICE_NAME: str = "MS2 criteria parser"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 60

    # MS1 Integration
    MS1_URL: str = "http://localhost:8001"
    MS1_TIMEOUT: int = 30

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ms2_db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # Parsing Configuration
    MIN_CONFIDENCE_THRESHOLD: float = 0.5
    COMPLEXITY_WORD_THRESHOLD: int = 200  # Switch to full model above this
    ENABLE_MEDICAL_CODING: bool = True

    # Medical Coding (optional)
    UMLS_API_KEY: Optional[str] = None



@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        return Settings() # type: ignore[call-arg]

    except Exception as e:
        raise RuntimeError(f"Failed to load settings: {e}") from e


settings = get_settings()


"""Configuration settings for MS2 microservice: clinical trial criteria parser."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    SERVICE_NAME: str = "MS2 criteria parser"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8002

    # Add your configuration variables here
    DATABASE_URL: str = "sqlite:///./ms2.db"
    API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()

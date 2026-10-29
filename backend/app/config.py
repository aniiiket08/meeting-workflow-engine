from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Information
    PROJECT_NAME: str = "Meeting Organizer Agent"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # LLM Settings
    LLM_MODEL: str = Field(
        default="gemini-3.1-flash-lite",
        description="Google Gemini model used for structured meeting workflows",
    )
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google AI Studio API key",
    )

    # Security
    SECRET_KEY: str = Field(
        default="super-secret-key-change-in-production",
        description="JWT secret key",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # App Environment
    APP_ENV: Literal["development", "production"] = Field(
        default="production",
        description="Application environment: 'development' enables dev-only features",
    )

    # Seed
    SEED_PASSWORD: str = Field(
        default="",
        description="Password used by the seed script for initial users (must be set in .env)",
    )

    # Outbound email. No delivery is attempted until SMTP is explicitly configured.
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_STARTTLS: bool = True

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./sql_app.db",
        description="SQLAlchemy database URL",
    )

    # Vector Storage
    CHROMADB_PATH: str = Field(
        default="./data/chroma",
        description="Path to ChromaDB persistent directory",
    )

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )


settings = Settings()

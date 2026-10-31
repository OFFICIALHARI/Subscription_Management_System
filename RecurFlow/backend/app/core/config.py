"""Application configuration and environment settings management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable fallback and strict production validation."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core Application
    APP_NAME: str = "RecurFlow"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database Configuration (PostgreSQL 17 on dedicated port 5434)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://recurflow:change_me@localhost:5434/recurflow",
        description="Database connection string formatted for SQLAlchemy 2 with psycopg driver.",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # Security & Authentication
    JWT_SECRET_KEY: str = Field(
        default="replace_with_a_long_random_secret_at_least_32_characters_long_for_security",
        description="Secret key for signing JWT tokens. Must be strong and protected.",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS Origins
    CORS_ORIGINS: list[str] | str = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="List of permitted CORS origins or comma-separated string.",
    )

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return []

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "Settings":
        """Fail fast if required security invariants are violated in non-dev environments."""
        if self.APP_ENV in ("production", "staging"):
            if "change_me" in self.DATABASE_URL:
                msg = "Production DATABASE_URL must not contain default placeholder credentials."
                raise ValueError(msg)
            if len(self.JWT_SECRET_KEY) < 32 or "replace_with" in self.JWT_SECRET_KEY:
                msg = "Production JWT_SECRET_KEY must be a secure secret >= 32 characters."
                raise ValueError(msg)
            if "*" in self.CORS_ORIGINS:
                msg = "Wildcard CORS origins are forbidden in production and staging."
                raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()


settings = get_settings()

"""Typed application settings loaded from the environment."""

from functools import lru_cache

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def parse_allowed_cors_origins(value: str) -> list[str]:
    origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*'.")
    return origins


def get_cors_origins_from_environment() -> list[str]:
    """Read CORS independently so the app can expose readiness failures."""
    return CorsSettings().allowed_origins()


def get_max_request_body_bytes_from_environment() -> int:
    """Read the body limit without requiring Jira or database secrets."""
    return CorsSettings().max_request_body_bytes


class CorsSettings(BaseSettings):
    """Startup-only CORS configuration with no secret dependencies."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cors_allowed_origins: str = Field(
        default=DEFAULT_CORS_ORIGINS,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    max_request_body_bytes: int = Field(
        default=1_048_576,
        validation_alias="MAX_REQUEST_BODY_BYTES",
        ge=1_024,
        le=10_485_760,
    )

    def allowed_origins(self) -> list[str]:
        return parse_allowed_cors_origins(self.cors_allowed_origins)


class Settings(BaseSettings):
    """Configuration required to communicate with Jira Cloud."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    jira_base_url: HttpUrl = Field(
        validation_alias="JIRA_BASE_URL",
    )
    jira_email: str = Field(
        min_length=1,
        validation_alias="JIRA_EMAIL",
    )
    jira_api_token: SecretStr = Field(
        validation_alias="JIRA_API_TOKEN",
    )
    database_url: str = Field(
        default="sqlite:///./data/jira_ai.db",
        validation_alias="DATABASE_URL",
        min_length=1,
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
        min_length=1,
    )
    ollama_model: str = Field(
        default="llama3.2",
        validation_alias="OLLAMA_MODEL",
        min_length=1,
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        validation_alias="OLLAMA_EMBEDDING_MODEL",
        min_length=1,
    )
    embedding_dimensions: int = Field(
        default=768,
        validation_alias="EMBEDDING_DIMENSIONS",
        ge=1,
    )
    jwt_secret_key: SecretStr = Field(
        validation_alias="JWT_SECRET_KEY",
        min_length=32,
    )
    jwt_access_token_minutes: int = Field(
        default=30,
        validation_alias="JWT_ACCESS_TOKEN_MINUTES",
        ge=5,
        le=1440,
    )
    cors_allowed_origins: str = Field(
        default=DEFAULT_CORS_ORIGINS,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    max_request_body_bytes: int = Field(
        default=1_048_576,
        validation_alias="MAX_REQUEST_BODY_BYTES",
        ge=1_024,
        le=10_485_760,
    )

    def allowed_cors_origins(self) -> list[str]:
        """Return normalized explicit origins; wildcards are not accepted."""
        return parse_allowed_cors_origins(self.cors_allowed_origins)


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once per application process."""
    # Pydantic supplies required values from the environment at runtime.
    return Settings()  # type: ignore[call-arg]

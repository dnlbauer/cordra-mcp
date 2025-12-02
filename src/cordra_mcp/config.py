"""Configuration settings for the MCP Cordra server."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CordraConfig(BaseSettings):
    """Configuration for connecting to a Cordra repository."""

    model_config = SettingsConfigDict(
        env_prefix="CORDRA_",
        case_sensitive=False,
    )

    base_url: str = Field(
        default="https://localhost:8443",
        description="Base URL of the Cordra repository",
    )
    username: str | None = Field(
        default=None, description="Username for Cordra authentication"
    )
    password: str | None = Field(
        default=None, description="Password for Cordra authentication"
    )
    verify_ssl: bool = Field(
        default=True, description="Whether to verify SSL certificates"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        validation_alias="LOGLEVEL",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log_level is a standard logging level."""
        level_str = str(v).upper().strip()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        if level_str not in valid_levels:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {', '.join(valid_levels)}"
            )
        return level_str

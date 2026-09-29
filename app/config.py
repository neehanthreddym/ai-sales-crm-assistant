from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed configuration; secrets remain wrapped and excluded from repr."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    environment: str = "development"
    log_level: str = "INFO"
    llm_provider: Literal["groq", "openai"] = "groq"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-20b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-mini"
    llm_timeout_seconds: float = Field(default=30, gt=0)
    hubspot_access_token: SecretStr | None = None
    hubspot_api_version: str = "2026-09"
    hubspot_base_url: str = "https://api.hubapi.com"
    hubspot_pipeline_id: str | None = None
    hubspot_initial_stage_id: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    google_sheets_worksheet: str = "Leads"
    google_application_credentials: str | None = None
    run_integration_tests: bool = False

    @field_validator("groq_api_key", "openai_api_key", "hubspot_access_token", mode="before")
    @classmethod
    def empty_secret_is_unconfigured(cls, value: object) -> object | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

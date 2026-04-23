from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    empresa_id: str = Field(..., alias="AGENT_EMPRESA_ID")
    api_base_url: str = Field(..., alias="AGENT_API_BASE_URL")
    api_key: str = Field(..., alias="AGENT_API_KEY")
    api_key_file: str | None = Field(default=None, alias="AGENT_API_KEY_FILE")
    mariadb_url: str = Field(..., alias="AGENT_MARIADB_URL")

    sync_interval_minutes: int = 15
    batch_size: int = 500
    timeout_seconds: int = 30
    verify_ssl: bool = True
    checkpoint_file: str = "agent_local/data/checkpoints.json"
    log_level: str = "INFO"
    source_query: str | None = Field(default=None, alias="AGENT_SOURCE_QUERY")
    audit_file: str | None = Field(default=None, alias="AGENT_AUDIT_FILE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_agent_settings() -> AgentSettings:
    return AgentSettings()

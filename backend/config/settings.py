from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "multi-tenant-sync-api"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = "INFO"

    database_url: str = Field(..., alias="DATABASE_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    api_key_header: str = "X-API-Key"
    empresa_header: str = "X-Empresa-Id"
    admin_token_header: str = "X-Admin-Token"
    admin_token: str = Field(..., alias="ADMIN_TOKEN")
    local_client_id_header: str = "X-Client-Id"
    local_client_token_header: str = "X-Client-Token"
    local_client_token_expiration_days: int = Field(
        default=90,
        alias="LOCAL_CLIENT_TOKEN_EXPIRATION_DAYS",
    )
    tenant_api_key_expiration_days: int = Field(
        default=90,
        alias="TENANT_API_KEY_EXPIRATION_DAYS",
    )
    tenant_api_key_expiration_enforced: bool = Field(
        default=True,
        alias="TENANT_API_KEY_EXPIRATION_ENFORCED",
    )
    tenant_config_encryption_key_file: str | None = Field(
        default=None,
        alias="TENANT_CONFIG_ENCRYPTION_KEY_FILE",
    )
    connection_secrets_file: str = Field(
        default="output/tenant_connection_secrets.json",
        alias="CONNECTION_SECRETS_FILE",
    )
    cors_allowed_origins: str = Field(
        default="http://localhost,http://127.0.0.1",
        alias="CORS_ALLOWED_ORIGINS",
    )
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(
        default=120,
        alias="RATE_LIMIT_REQUESTS_PER_MINUTE",
    )

    retention_months: int = 14
    retention_mode: Literal["delete", "archive"] = "archive"
    retention_job_interval_minutes: int = 60
    retention_job_enabled: bool = True

    batch_max_size: int = 1000
    sync_ingest_chunk_size: int = Field(
        default=250,
        alias="SYNC_INGEST_CHUNK_SIZE",
    )
    tenant_worker_max_workers: int = Field(
        default=4,
        alias="TENANT_WORKER_MAX_WORKERS",
    )
    tenant_worker_max_jobs_per_tenant: int = Field(
        default=2,
        alias="TENANT_WORKER_MAX_JOBS_PER_TENANT",
    )
    tenant_queue_max_pending_per_empresa: int = Field(
        default=20,
        alias="TENANT_QUEUE_MAX_PENDING_PER_EMPRESA",
    )
    auto_create_tables: bool = False
    memory_database_url: str = Field(
        default="sqlite+pysqlite:///./output/cerebro_vivo.db",
        alias="MEMORY_DATABASE_URL",
    )
    memory_json_backup_path: str = Field(
        default=".cerebro-vivo/Logs/memory_standard.json",
        alias="MEMORY_JSON_BACKUP_PATH",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.environment.lower() != "production":
            return self
        forbidden = {
            "secret_key": {"change-me"},
            "admin_token": {"change-this-admin-token"},
        }
        for field_name, invalid_values in forbidden.items():
            value = getattr(self, field_name)
            if value in invalid_values:
                raise ValueError(f"{field_name} must be set to a non-placeholder value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

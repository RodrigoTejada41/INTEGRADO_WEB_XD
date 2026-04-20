from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "multi-tenant-sync-api"
    environment: str = "production"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    database_url: str = Field(..., alias="DATABASE_URL")
    api_key_header: str = "X-API-Key"
    empresa_header: str = "X-Empresa-Id"
    admin_token_header: str = "X-Admin-Token"
    admin_token: str = Field(..., alias="ADMIN_TOKEN")

    retention_months: int = 14
    retention_mode: Literal["delete", "archive"] = "archive"
    retention_job_interval_minutes: int = 60
    retention_job_enabled: bool = True

    batch_max_size: int = 1000
    auto_create_tables: bool = False
    jwt_secret: str = Field("change-this-jwt-secret", alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_access_expires_minutes: int = 30
    jwt_refresh_expires_minutes: int = 10080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

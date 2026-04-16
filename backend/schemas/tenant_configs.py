from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=120)
    connector_type: str = Field(min_length=2, max_length=32)
    sync_interval_minutes: int = Field(default=15, ge=1, le=1440)
    settings: dict[str, str] = Field(default_factory=dict)


class TenantConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    connector_type: str | None = Field(default=None, min_length=2, max_length=32)
    sync_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    settings: dict[str, str] | None = None
    ativo: bool | None = None


class TenantConfigResponse(BaseModel):
    id: str
    empresa_id: str
    nome: str
    connector_type: str
    sync_interval_minutes: int
    settings: dict[str, str]
    ativo: bool
    last_run_at: datetime | None
    last_status: str
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class TenantConfigDeleteResponse(BaseModel):
    id: str
    empresa_id: str
    status: str

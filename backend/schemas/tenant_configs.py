from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=120)
    connector_type: str = Field(min_length=2, max_length=32)
    settings: dict[str, str] = Field(default_factory=dict)


class TenantConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=120)
    connector_type: str | None = Field(default=None, min_length=2, max_length=32)
    settings: dict[str, str] | None = None
    ativo: bool | None = None


class TenantConfigResponse(BaseModel):
    id: str
    empresa_id: str
    nome: str
    connector_type: str
    settings: dict[str, str]
    ativo: bool
    created_at: datetime
    updated_at: datetime


class TenantConfigDeleteResponse(BaseModel):
    id: str
    empresa_id: str
    status: str

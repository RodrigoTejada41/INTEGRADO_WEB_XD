from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LocalClientRegistrationRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=36)
    hostname: str = Field(min_length=1, max_length=255)
    ip: str | None = Field(default=None, max_length=64)
    endpoint_url: str | None = Field(default=None, max_length=255)
    token: str = Field(min_length=32, max_length=256)
    token_expires_at: datetime | None = None
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    status_snapshot: dict[str, object] = Field(default_factory=dict)


class LocalClientHeartbeatRequest(BaseModel):
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    status_snapshot: dict[str, object] = Field(default_factory=dict)


class LocalClientCommandResultRequest(BaseModel):
    status: str = Field(pattern="^(completed|failed)$")
    result: dict[str, object] = Field(default_factory=dict)
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    status_snapshot: dict[str, object] = Field(default_factory=dict)


class LocalClientCommandPayload(BaseModel):
    id: str
    client_id: str
    empresa_id: str
    command_type: str
    payload: dict[str, object] = Field(default_factory=dict)
    status: str
    requested_by: str
    origin: str
    created_at: datetime
    delivered_at: datetime | None = None
    executed_at: datetime | None = None


class LocalClientResponse(BaseModel):
    id: str
    empresa_id: str
    empresa_nome: str | None = None
    hostname: str
    ip_address: str | None = None
    endpoint_url: str | None = None
    status: str
    last_seen_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_command_poll_at: datetime | None = None
    config_snapshot: dict[str, object] = Field(default_factory=dict)
    status_snapshot: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LocalClientFleetSummaryResponse(BaseModel):
    total_clients: int
    online_clients: int
    error_clients: int
    unique_empresas: int


class LocalClientConfigUpdateRequest(BaseModel):
    payload: dict[str, object] = Field(default_factory=dict)


class LocalClientActionResponse(BaseModel):
    status: str
    client_id: str
    command_id: str


class LocalClientRegistrationResponse(BaseModel):
    status: str
    client_id: str
    empresa_id: str
    token_expires_at: datetime | None = None


class LocalClientLogResponse(BaseModel):
    id: str
    client_id: str
    empresa_id: str
    direction: str
    event_type: str
    origin: str
    status: str
    message: str | None = None
    correlation_id: str | None = None
    detail: dict[str, object] = Field(default_factory=dict)
    created_at: datetime

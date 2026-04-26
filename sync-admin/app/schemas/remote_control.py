from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LocalConfigResponse(BaseModel):
    installation_id: str
    empresa_id: str
    empresa_nome: str
    control_api_base_url: str
    local_endpoint_url: str
    sync_interval_minutes: int
    command_poll_interval_seconds: int
    registration_interval_seconds: int
    remote_control_allowed_ips: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None


class LocalConfigUpdateRequest(BaseModel):
    control_api_base_url: str | None = None
    local_endpoint_url: str | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    command_poll_interval_seconds: int | None = Field(default=None, ge=5, le=3600)
    registration_interval_seconds: int | None = Field(default=None, ge=30, le=86400)
    remote_control_allowed_ips: list[str] | None = None


class LocalStatusResponse(BaseModel):
    service: str
    installation_id: str
    empresa_id: str
    hostname: str
    uptime_seconds: int
    started_at: datetime
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None
    last_sync_reason: str | None = None
    last_registration_at: datetime | None = None
    last_command_poll_at: datetime | None = None
    last_command_origin: str | None = None
    pending_local_batches: int
    total_local_records: int


class ForceSyncResponse(BaseModel):
    status: str
    detail: str
    last_sync_at: datetime | None = None

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TenantJobSummaryResponse(BaseModel):
    empresa_id: str
    pending_count: int
    processing_count: int
    done_count: int
    dead_letter_count: int
    failed_count: int


class TenantJobResponse(BaseModel):
    id: str
    empresa_id: str
    source_config_id: str
    status: str
    attempts: int
    scheduled_at: datetime
    next_run_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    dead_letter_at: datetime | None
    dead_letter_reason: str | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class TenantJobRetryResponse(BaseModel):
    id: str
    empresa_id: str
    status: str
    next_run_at: datetime
    attempts: int

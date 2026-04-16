from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SyncRecordIn(BaseModel):
    record_key: str = Field(min_length=1, max_length=120)
    record_type: str = Field(min_length=1, max_length=80)
    event_time: datetime | None = None
    payload: dict[str, Any]


class SyncPayloadIn(BaseModel):
    external_batch_id: str | None = Field(default=None, max_length=120)
    company_code: str = Field(min_length=1, max_length=50)
    branch_code: str = Field(min_length=1, max_length=50)
    terminal_code: str = Field(min_length=1, max_length=50)
    sent_at: datetime | None = None
    records: list[SyncRecordIn] = Field(default_factory=list)

from datetime import datetime

from pydantic import BaseModel


class TenantAuditEventResponse(BaseModel):
    id: str
    empresa_id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    status: str
    detail: dict[str, str]
    created_at: datetime


class TenantAuditSummaryResponse(BaseModel):
    empresa_id: str
    total_count: int
    success_count: int
    failure_count: int
    actors: list[str]
    actions: list[str]

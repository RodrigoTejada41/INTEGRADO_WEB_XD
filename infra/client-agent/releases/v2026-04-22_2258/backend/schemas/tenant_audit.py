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
    correlation_id: str | None
    request_path: str | None
    actor_ip: str | None
    user_agent: str | None
    detail: dict[str, object]
    created_at: datetime


class TenantAuditSummaryResponse(BaseModel):
    empresa_id: str
    total_count: int
    success_count: int
    failure_count: int
    actors: list[str]
    actions: list[str]

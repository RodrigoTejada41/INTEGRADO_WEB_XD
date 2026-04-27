from __future__ import annotations

import json

from backend.repositories.tenant_audit_repository import TenantAuditRepository
from backend.schemas.tenant_audit import TenantAuditEventResponse, TenantAuditSummaryResponse


class TenantAuditService:
    def __init__(self, repository: TenantAuditRepository):
        self.repository = repository

    @staticmethod
    def _to_response(item) -> TenantAuditEventResponse:
        return TenantAuditEventResponse(
            id=item.id,
            empresa_id=item.empresa_id,
            actor=item.actor,
            action=item.action,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            status=item.status,
            correlation_id=item.correlation_id,
            request_path=item.request_path,
            actor_ip=item.actor_ip,
            user_agent=item.user_agent,
            detail=json.loads(item.detail_json or "{}"),
            created_at=item.created_at,
        )

    def record(
        self,
        *,
        empresa_id: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        status: str = "success",
        correlation_id: str | None = None,
        request_path: str | None = None,
        actor_ip: str | None = None,
        user_agent: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> TenantAuditEventResponse:
        item = self.repository.create(
            empresa_id=empresa_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            correlation_id=correlation_id,
            request_path=request_path,
            actor_ip=actor_ip,
            user_agent=user_agent,
            detail=detail,
        )
        return self._to_response(item)

    def list_recent(self, empresa_id: str, limit: int = 20) -> list[TenantAuditEventResponse]:
        items = self.repository.list_by_empresa_id(empresa_id, limit=limit)
        return [self._to_response(item) for item in items]

    def summary(self, empresa_id: str) -> TenantAuditSummaryResponse:
        data = self.repository.summary_by_empresa_id(empresa_id)
        return TenantAuditSummaryResponse(
            empresa_id=empresa_id,
            total_count=int(data.get("total_count", 0)),
            success_count=int(data.get("success_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            actors=[str(item) for item in data.get("actors", [])],
            actions=[str(item) for item in data.get("actions", [])],
        )

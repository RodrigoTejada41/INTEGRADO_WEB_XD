from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models.tenant_audit_event import TenantAuditEvent


class TenantAuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
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
    ) -> TenantAuditEvent:
        item = TenantAuditEvent(
            id=str(uuid4()),
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
            detail_json=json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
            created_at=datetime.now(UTC),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def list_by_empresa_id(self, empresa_id: str, limit: int = 20) -> list[TenantAuditEvent]:
        stmt = (
            select(TenantAuditEvent)
            .where(TenantAuditEvent.empresa_id == empresa_id)
            .order_by(TenantAuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def summary_by_empresa_id(self, empresa_id: str) -> dict[str, object]:
        stmt = select(
            func.count(TenantAuditEvent.id),
            func.sum(case((TenantAuditEvent.status == "success", 1), else_=0)),
            func.sum(case((TenantAuditEvent.status == "failure", 1), else_=0)),
        ).where(TenantAuditEvent.empresa_id == empresa_id)
        row = self.session.execute(stmt).one()
        actor_stmt = (
            select(TenantAuditEvent.actor)
            .where(TenantAuditEvent.empresa_id == empresa_id)
            .distinct()
            .order_by(TenantAuditEvent.actor)
        )
        action_stmt = (
            select(TenantAuditEvent.action)
            .where(TenantAuditEvent.empresa_id == empresa_id)
            .distinct()
            .order_by(TenantAuditEvent.action)
        )
        return {
            "total_count": int(row[0] or 0),
            "success_count": int(row[1] or 0),
            "failure_count": int(row[2] or 0),
            "actors": list(self.session.scalars(actor_stmt).all()),
            "actions": list(self.session.scalars(action_stmt).all()),
        }

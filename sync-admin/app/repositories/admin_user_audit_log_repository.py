from __future__ import annotations

import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.admin_user_audit_log import AdminUserAuditLog


class AdminUserAuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        actor: str,
        action: str,
        resource_id: str,
        target_username: str,
        detail: dict[str, object] | None = None,
        status: str = "success",
        correlation_id: str | None = None,
        request_path: str | None = None,
        actor_ip: str | None = None,
        user_agent: str | None = None,
    ) -> AdminUserAuditLog:
        row = AdminUserAuditLog(
            actor=actor,
            action=action,
            resource_id=resource_id,
            target_username=target_username,
            status=status,
            correlation_id=correlation_id,
            request_path=request_path,
            actor_ip=actor_ip,
            user_agent=user_agent,
            detail_json=json.dumps(detail or {}, ensure_ascii=True, sort_keys=True),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_recent(self, limit: int = 10) -> list[AdminUserAuditLog]:
        stmt = select(AdminUserAuditLog).order_by(desc(AdminUserAuditLog.created_at), desc(AdminUserAuditLog.id)).limit(limit)
        return list(self.db.scalars(stmt).all())

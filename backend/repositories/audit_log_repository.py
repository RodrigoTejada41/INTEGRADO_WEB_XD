from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        return log

    def list_recent_by_empresa(self, empresa_id: str, limit: int = 50) -> list[AuditLog]:
        return list(
            self.session.scalars(
                select(AuditLog).where(AuditLog.empresa_id == empresa_id).order_by(AuditLog.created_at.desc()).limit(limit)
            )
        )

import json
import uuid

from backend.models.audit_log import AuditLog
from backend.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    def log(self, empresa_id: str, user_id: str, action: str, resource: str, detail: dict) -> None:
        self.repository.add(
            AuditLog(
                id=str(uuid.uuid4()),
                empresa_id=empresa_id,
                user_id=user_id,
                action=action,
                resource=resource,
                detail=json.dumps(detail, ensure_ascii=False),
            )
        )

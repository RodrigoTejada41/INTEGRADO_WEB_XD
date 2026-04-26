from __future__ import annotations

import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.remote_command_log import RemoteCommandLog


class RemoteCommandLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        command_id: str | None,
        command_type: str,
        origin: str,
        status: str,
        detail: dict[str, object] | None = None,
    ) -> RemoteCommandLog:
        entity = RemoteCommandLog(
            command_id=command_id,
            command_type=command_type,
            origin=origin,
            status=status,
            detail_json=json.dumps(detail or {}, ensure_ascii=False, sort_keys=True),
        )
        self.db.add(entity)
        self.db.flush()
        return entity

    def list_recent(self, limit: int = 20) -> list[RemoteCommandLog]:
        stmt = select(RemoteCommandLog).order_by(desc(RemoteCommandLog.created_at)).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

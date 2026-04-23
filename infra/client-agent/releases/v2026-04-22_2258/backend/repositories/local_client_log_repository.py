from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.local_client_log import LocalClientLog
from backend.utils.correlation import get_correlation_id


class LocalClientLogRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        client_id: str,
        empresa_id: str,
        direction: str,
        event_type: str,
        origin: str,
        status: str,
        message: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> LocalClientLog:
        payload_detail = dict(detail or {})
        correlation_id = get_correlation_id()
        if correlation_id:
            payload_detail.setdefault("correlation_id", correlation_id)
        entity = LocalClientLog(
            id=str(uuid4()),
            client_id=client_id,
            empresa_id=empresa_id,
            direction=direction,
            event_type=event_type,
            origin=origin,
            status=status,
            message=message,
            detail_json=json.dumps(payload_detail, ensure_ascii=False, sort_keys=True),
            created_at=datetime.now(UTC),
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_recent(self, client_id: str, limit: int = 20) -> list[LocalClientLog]:
        stmt = (
            select(LocalClientLog)
            .where(LocalClientLog.client_id == client_id)
            .order_by(LocalClientLog.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

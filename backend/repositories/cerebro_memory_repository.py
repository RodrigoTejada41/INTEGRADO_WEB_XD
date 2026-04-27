from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.models.cerebro_memory_record import CerebroMemoryHistory, CerebroMemoryRecord


class CerebroMemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_project_tag(self, project_tag: str) -> CerebroMemoryRecord | None:
        return self._session.get(CerebroMemoryRecord, project_tag)

    @property
    def session(self) -> Session:
        return self._session

    def upsert(
        self,
        project_tag: str,
        payload_json: str,
        source_priority: str = "API>DB>JSON",
    ) -> CerebroMemoryRecord:
        record = self.get_by_project_tag(project_tag)
        if record is None:
            record = CerebroMemoryRecord(
                project_tag=project_tag,
                payload_json=payload_json,
                source_priority=source_priority,
                updated_at=datetime.now(UTC),
            )
            self._session.add(record)
        else:
            record.payload_json = payload_json
            record.source_priority = source_priority
            record.updated_at = datetime.now(UTC)

        history = CerebroMemoryHistory(
            project_tag=project_tag,
            payload_json=payload_json,
            source="api",
        )
        self._session.add(history)
        self._session.flush()
        return record

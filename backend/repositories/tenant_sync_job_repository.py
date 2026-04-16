from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.tenant_sync_job import TenantSyncJob


class TenantSyncJobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        job_id: str,
        empresa_id: str,
        source_config_id: str,
        payload_json: str,
        scheduled_at: datetime,
    ) -> TenantSyncJob:
        job = TenantSyncJob(
            id=job_id,
            empresa_id=empresa_id,
            source_config_id=source_config_id,
            status="pending",
            payload_json=payload_json,
            scheduled_at=scheduled_at,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def list_pending(self, limit: int = 100) -> list[TenantSyncJob]:
        stmt = (
            select(TenantSyncJob)
            .where(TenantSyncJob.status == "pending")
            .order_by(TenantSyncJob.scheduled_at, TenantSyncJob.created_at)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, job_id: str) -> TenantSyncJob | None:
        return self.session.get(TenantSyncJob, job_id)

    def mark_processing(self, job: TenantSyncJob) -> None:
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        self.session.flush()

    def mark_done(self, job: TenantSyncJob) -> None:
        job.status = "done"
        job.finished_at = datetime.now(UTC)
        job.last_error = None
        self.session.flush()

    def mark_failed(self, job: TenantSyncJob, error_message: str) -> None:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.last_error = error_message
        self.session.flush()

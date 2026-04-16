from __future__ import annotations

from datetime import UTC, datetime, timedelta
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
            next_run_at=scheduled_at,
        )
        self.session.add(job)
        self.session.flush()
        return job

    def list_pending(self, limit: int = 100) -> list[TenantSyncJob]:
        now = datetime.now(UTC)
        stmt = (
            select(TenantSyncJob)
            .where(TenantSyncJob.status == "pending")
            .order_by(TenantSyncJob.next_run_at, TenantSyncJob.created_at)
            .limit(limit)
        )
        jobs = list(self.session.scalars(stmt).all())
        ready_jobs: list[TenantSyncJob] = []
        for job in jobs:
            next_run_at = job.next_run_at
            if next_run_at.tzinfo is None:
                next_run_at = next_run_at.replace(tzinfo=UTC)
            if next_run_at <= now:
                ready_jobs.append(job)
        return ready_jobs

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

    def mark_retry(self, job: TenantSyncJob, error_message: str, backoff_minutes: int) -> None:
        job.status = "pending"
        job.finished_at = None
        job.last_error = error_message
        job.next_run_at = datetime.now(UTC) + timedelta(minutes=backoff_minutes)
        self.session.flush()

    def mark_dead_letter(self, job: TenantSyncJob, error_message: str) -> None:
        job.status = "dead_letter"
        job.finished_at = datetime.now(UTC)
        job.dead_letter_at = job.finished_at
        job.dead_letter_reason = error_message
        job.last_error = error_message
        self.session.flush()

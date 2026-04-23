from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
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
        self.recover_expired_leases()
        stmt = (
            select(TenantSyncJob)
            .where(
                TenantSyncJob.status == "pending",
                or_(TenantSyncJob.next_run_at.is_(None), TenantSyncJob.next_run_at <= now),
            )
            .order_by(TenantSyncJob.next_run_at, TenantSyncJob.created_at)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_pending_with_backpressure(
        self,
        *,
        limit: int = 100,
        per_tenant_limit: int = 2,
    ) -> list[TenantSyncJob]:
        now = datetime.now(UTC)
        self.recover_expired_leases()
        stmt = (
            select(TenantSyncJob)
            .where(
                TenantSyncJob.status == "pending",
                or_(TenantSyncJob.next_run_at.is_(None), TenantSyncJob.next_run_at <= now),
            )
            .order_by(TenantSyncJob.next_run_at, TenantSyncJob.created_at)
            .limit(max(limit * 10, limit))
        )
        rows = list(self.session.scalars(stmt).all())
        if per_tenant_limit <= 0:
            return rows[:limit]

        buckets: dict[str, list[TenantSyncJob]] = {}
        tenant_order: list[str] = []
        for job in rows:
            bucket = buckets.setdefault(job.empresa_id, [])
            if not bucket:
                tenant_order.append(job.empresa_id)
            bucket.append(job)

        selected: list[TenantSyncJob] = []
        selected_per_tenant: dict[str, int] = {tenant_id: 0 for tenant_id in tenant_order}

        while len(selected) < limit:
            progressed = False
            for tenant_id in tenant_order:
                if selected_per_tenant[tenant_id] >= per_tenant_limit:
                    continue
                bucket = buckets.get(tenant_id, [])
                if not bucket:
                    continue
                selected.append(bucket.pop(0))
                selected_per_tenant[tenant_id] += 1
                progressed = True
                if len(selected) >= limit:
                    break
            if not progressed:
                break

        return selected

    def recover_expired_leases(self) -> int:
        now = datetime.now(UTC)
        stmt = select(TenantSyncJob).where(
            TenantSyncJob.status == "processing",
            TenantSyncJob.lease_expires_at.is_not(None),
            TenantSyncJob.lease_expires_at <= now,
        )
        jobs = list(self.session.scalars(stmt).all())
        for job in jobs:
            job.status = "pending"
            job.leased_by = None
            job.lease_expires_at = None
            job.started_at = None
        if jobs:
            self.session.flush()
        return len(jobs)

    def get_by_id(self, job_id: str) -> TenantSyncJob | None:
        return self.session.get(TenantSyncJob, job_id)

    def get_summary_by_empresa_id(self, empresa_id: str) -> dict[str, int]:
        stmt = (
            select(TenantSyncJob.status, func.count(TenantSyncJob.id))
            .where(TenantSyncJob.empresa_id == empresa_id)
            .group_by(TenantSyncJob.status)
        )
        rows = self.session.execute(stmt).all()
        summary = {
            "pending": 0,
            "processing": 0,
            "done": 0,
            "dead_letter": 0,
            "failed": 0,
        }
        for status, count in rows:
            summary[str(status)] = int(count or 0)
        return summary

    def get_pending_count_by_empresa_id(self, empresa_id: str) -> int:
        stmt = select(func.count(TenantSyncJob.id)).where(
            TenantSyncJob.empresa_id == empresa_id,
            TenantSyncJob.status == "pending",
        )
        return int(self.session.scalar(stmt) or 0)

    def list_by_empresa_id(self, empresa_id: str, *, statuses: list[str] | None = None, limit: int = 20) -> list[TenantSyncJob]:
        stmt = select(TenantSyncJob).where(TenantSyncJob.empresa_id == empresa_id)
        if statuses:
            stmt = stmt.where(TenantSyncJob.status.in_(statuses))
        stmt = stmt.order_by(TenantSyncJob.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def mark_processing(self, job: TenantSyncJob, *, worker_id: str | None = None, lease_minutes: int = 15) -> None:
        job.status = "processing"
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        job.leased_by = worker_id
        job.lease_expires_at = datetime.now(UTC) + timedelta(minutes=lease_minutes)
        self.session.flush()

    def mark_done(self, job: TenantSyncJob) -> None:
        job.status = "done"
        job.finished_at = datetime.now(UTC)
        job.last_error = None
        job.leased_by = None
        job.lease_expires_at = None
        self.session.flush()

    def mark_retry(self, job: TenantSyncJob, error_message: str, backoff_minutes: int) -> None:
        job.status = "pending"
        job.finished_at = None
        job.last_error = error_message
        job.next_run_at = datetime.now(UTC) + timedelta(minutes=backoff_minutes)
        job.leased_by = None
        job.lease_expires_at = None
        self.session.flush()

    def mark_dead_letter(self, job: TenantSyncJob, error_message: str) -> None:
        job.status = "dead_letter"
        job.finished_at = datetime.now(UTC)
        job.dead_letter_at = job.finished_at
        job.dead_letter_reason = error_message
        job.last_error = error_message
        job.leased_by = None
        job.lease_expires_at = None
        self.session.flush()

    def requeue_job(self, job: TenantSyncJob) -> TenantSyncJob:
        job.status = "pending"
        job.attempts = 0
        job.last_error = None
        job.dead_letter_at = None
        job.dead_letter_reason = None
        job.started_at = None
        job.finished_at = None
        job.next_run_at = datetime.now(UTC)
        job.leased_by = None
        job.lease_expires_at = None
        self.session.flush()
        return job

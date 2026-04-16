from __future__ import annotations

from fastapi import HTTPException, status

from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.schemas.tenant_jobs import (
    TenantJobResponse,
    TenantJobRetryResponse,
    TenantJobSummaryResponse,
)
from backend.utils.security import validate_empresa_id


class TenantJobService:
    def __init__(self, repository: TenantSyncJobRepository):
        self.repository = repository

    @staticmethod
    def _to_response(job) -> TenantJobResponse:
        return TenantJobResponse(
            id=job.id,
            empresa_id=job.empresa_id,
            source_config_id=job.source_config_id,
            status=job.status,
            attempts=job.attempts,
            scheduled_at=job.scheduled_at,
            next_run_at=job.next_run_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            dead_letter_at=job.dead_letter_at,
            dead_letter_reason=job.dead_letter_reason,
            last_error=job.last_error,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def get_summary(self, empresa_id: str) -> TenantJobSummaryResponse:
        self._ensure_empresa_id(empresa_id)
        summary = self.repository.get_summary_by_empresa_id(empresa_id)
        return TenantJobSummaryResponse(
            empresa_id=empresa_id,
            pending_count=summary.get("pending", 0),
            processing_count=summary.get("processing", 0),
            done_count=summary.get("done", 0),
            dead_letter_count=summary.get("dead_letter", 0),
            failed_count=summary.get("failed", 0),
        )

    def list_dead_letters(self, empresa_id: str, limit: int = 10) -> list[TenantJobResponse]:
        self._ensure_empresa_id(empresa_id)
        jobs = self.repository.list_by_empresa_id(empresa_id, statuses=["dead_letter"], limit=limit)
        return [self._to_response(job) for job in jobs]

    def retry_job(self, empresa_id: str, job_id: str) -> TenantJobRetryResponse:
        self._ensure_empresa_id(empresa_id)
        job = self.repository.get_by_id(job_id)
        if job is None or job.empresa_id != empresa_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job nao encontrado.")
        if job.status not in {"dead_letter", "failed"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Somente jobs falhos ou em dead letter podem ser reenfileirados.",
            )
        job = self.repository.requeue_job(job)
        return TenantJobRetryResponse(
            id=job.id,
            empresa_id=job.empresa_id,
            status=job.status,
            next_run_at=job.next_run_at,
            attempts=job.attempts,
        )

    @staticmethod
    def _ensure_empresa_id(empresa_id: str) -> None:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )

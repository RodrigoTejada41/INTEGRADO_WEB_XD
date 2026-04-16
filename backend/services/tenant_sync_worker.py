from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from backend.models.tenant_source_config import TenantSourceConfig
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.utils.metrics import metrics_registry

logger = logging.getLogger(__name__)


class TenantSyncWorker:
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def drain_pending_jobs(self, limit: int = 100) -> int:
        processed = 0
        with self.session_factory() as session:
            job_repository = TenantSyncJobRepository(session)
            jobs = job_repository.list_pending(limit=limit)
            for job in jobs:
                job_repository.mark_processing(job)
                try:
                    payload = json.loads(job.payload_json)
                    source_config = session.get(TenantSourceConfig, job.source_config_id)
                    if source_config is None:
                        raise RuntimeError("source_config nao encontrado")
                    source_config.last_run_at = datetime.now(UTC)
                    source_config.last_status = "ok"
                    source_config.last_error = None
                    job_repository.mark_done(job)
                    metrics_registry.record_tenant_queue_processed(job.empresa_id)
                    logger.info(
                        "tenant_sync_job_completed",
                        extra={"empresa_id": job.empresa_id, "job_id": job.id, "payload": payload},
                    )
                    processed += 1
                except Exception as exc:
                    job_repository.mark_failed(job, str(exc))
                    metrics_registry.record_tenant_queue_failed(job.empresa_id)
                    logger.exception(
                        "tenant_sync_job_failed",
                        extra={"empresa_id": job.empresa_id, "job_id": job.id},
                    )
            session.commit()
        return processed

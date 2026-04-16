from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.connectors.source_connectors import get_default_source_connector_registry
from backend.models.tenant_source_config import TenantSourceConfig
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.repositories.venda_repository import VendaRepository
from backend.services.tenant_destination_dispatcher import TenantDestinationDispatcher
from backend.utils.crypto import decrypt_json
from backend.utils.metrics import metrics_registry

logger = logging.getLogger(__name__)


class TenantSyncWorker:
    MAX_ATTEMPTS = 3
    BASE_BACKOFF_MINUTES = 5

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self.connector_registry = get_default_source_connector_registry()
        self.destination_dispatcher = TenantDestinationDispatcher(session_factory)

    def drain_pending_jobs(self, limit: int = 100) -> int:
        processed = 0
        with self.session_factory() as session:
            job_repository = TenantSyncJobRepository(session)
            jobs = job_repository.list_pending(limit=limit)
            for job in jobs:
                job_repository.mark_processing(job)
                session.commit()
                try:
                    source_config = session.scalar(
                        select(TenantSourceConfig).where(TenantSourceConfig.id == job.source_config_id)
                    )
                    if source_config is None:
                        raise RuntimeError("source_config nao encontrado")
                    source_settings = decrypt_json(source_config.settings_json)
                    connector = self.connector_registry.get(source_config.connector_type)
                    since = source_config.last_run_at or datetime.now(UTC) - timedelta(days=3650)
                    fetch_result = connector.fetch_records(
                        settings=source_settings,
                        empresa_id=job.empresa_id,
                        since=since,
                        limit=int(source_settings.get("batch_size", "500")),
                    )
                    records = [self._normalize_record(record) for record in fetch_result.records]
                    venda_repository = VendaRepository(session)
                    inserted_count, updated_count = venda_repository.bulk_upsert(
                        empresa_id=job.empresa_id,
                        records=records,
                    )
                    session.commit()
                    self.destination_dispatcher.dispatch_records(job.empresa_id, records)
                    source_config.last_run_at = datetime.now(UTC)
                    source_config.last_status = "ok"
                    source_config.last_error = None
                    job_repository.mark_done(job)
                    metrics_registry.record_sync_success(
                        empresa_id=job.empresa_id,
                        inserted_count=inserted_count,
                        updated_count=updated_count,
                    )
                    metrics_registry.record_tenant_queue_processed(job.empresa_id)
                    logger.info(
                        "tenant_sync_job_completed",
                        extra={
                            "empresa_id": job.empresa_id,
                            "job_id": job.id,
                            "connector_type": source_config.connector_type,
                            "inserted_count": inserted_count,
                            "updated_count": updated_count,
                        },
                    )
                    processed += 1
                except Exception as exc:
                    session.rollback()
                    source_config = session.scalar(
                        select(TenantSourceConfig).where(TenantSourceConfig.id == job.source_config_id)
                    )
                    if source_config is not None:
                        source_config.last_status = "retrying" if job.attempts < self.MAX_ATTEMPTS else "dead_letter"
                        source_config.last_error = str(exc)
                    metrics_registry.record_tenant_queue_failed(job.empresa_id)
                    if job.attempts < self.MAX_ATTEMPTS:
                        backoff_minutes = self.BASE_BACKOFF_MINUTES * (2 ** (job.attempts - 1))
                        job_repository.mark_retry(job, str(exc), backoff_minutes=backoff_minutes)
                        metrics_registry.record_tenant_queue_retried(job.empresa_id)
                        logger.exception(
                            "tenant_sync_job_retry_scheduled",
                            extra={
                                "empresa_id": job.empresa_id,
                                "job_id": job.id,
                                "backoff_minutes": backoff_minutes,
                            },
                        )
                    else:
                        job_repository.mark_dead_letter(job, str(exc))
                        metrics_registry.record_tenant_queue_dead_letter(job.empresa_id)
                        logger.exception(
                            "tenant_sync_job_dead_letter",
                            extra={"empresa_id": job.empresa_id, "job_id": job.id},
                        )
            session.commit()
        return processed

    @staticmethod
    def _normalize_record(record: dict) -> dict:
        normalized = dict(record)
        data_value = normalized.get("data")
        if isinstance(data_value, str):
            normalized["data"] = date.fromisoformat(data_value)

        updated_value = normalized.get("data_atualizacao")
        if isinstance(updated_value, str):
            parsed = datetime.fromisoformat(updated_value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            normalized["data_atualizacao"] = parsed

        normalized["valor"] = str(normalized["valor"])
        return normalized

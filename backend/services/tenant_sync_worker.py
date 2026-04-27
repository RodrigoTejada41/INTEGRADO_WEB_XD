from __future__ import annotations

import logging
import json
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
import http

import httpx
from sqlalchemy.exc import OperationalError
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.connectors.source_connectors import get_default_source_connector_registry
from backend.models.tenant_source_config import TenantSourceConfig
from backend.repositories.tenant_audit_repository import TenantAuditRepository
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.repositories.venda_repository import VendaRepository
from backend.services.tenant_destination_dispatcher import TenantDestinationDispatcher
from backend.utils.correlation import bind_correlation_id, bind_log_context
from backend.utils.crypto import decrypt_json
from backend.utils.metrics import metrics_registry
from backend.utils.settings_resolver import resolve_runtime_settings

logger = logging.getLogger(__name__)


class TenantSyncWorker:
    DEFAULT_MAX_ATTEMPTS = 5
    BASE_BACKOFF_MINUTES = 2
    LEASE_MINUTES = 15

    def __init__(
        self,
        session_factory: sessionmaker,
        max_workers: int = 4,
        chunk_size: int = 250,
        max_jobs_per_tenant: int = 2,
    ):
        self.session_factory = session_factory
        self.max_workers = max_workers
        self.chunk_size = max(1, chunk_size)
        self.max_jobs_per_tenant = max(1, max_jobs_per_tenant)
        self.connector_registry = get_default_source_connector_registry()
        self.destination_dispatcher = TenantDestinationDispatcher(session_factory)

    def drain_pending_jobs(self, limit: int = 100, max_workers: int | None = None) -> int:
        worker_count = max(1, max_workers or self.max_workers)
        with self.session_factory() as session:
            job_repository = TenantSyncJobRepository(session)
            jobs = job_repository.list_pending_with_backpressure(
                limit=limit,
                per_tenant_limit=self.max_jobs_per_tenant,
            )
            for job in jobs:
                job_repository.mark_processing(
                    job,
                    worker_id=f"tenant-sync-worker-{job.id}",
                    lease_minutes=self.LEASE_MINUTES,
                )
            session.commit()

        if not jobs:
            return 0

        processed = 0
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures: list[Future[int]] = [
                executor.submit(self._process_job, job.id) for job in jobs
            ]
            for future in as_completed(futures):
                try:
                    processed += future.result()
                except Exception:
                    logger.exception("tenant_sync_worker_future_failed")
        return processed

    def _process_job(self, job_id: str) -> int:
        with self.session_factory() as session:
            job_repository = TenantSyncJobRepository(session)
            job = job_repository.get_by_id(job_id)
            if job is None:
                return 0
            correlation_id = f"wrk-{job.id}"
            try:
                payload = json.loads(job.payload_json or "{}")
                payload_correlation_id = payload.get("correlation_id")
                if isinstance(payload_correlation_id, str) and payload_correlation_id.strip():
                    correlation_id = payload_correlation_id.strip()
            except json.JSONDecodeError:
                pass

            with bind_correlation_id(correlation_id), bind_log_context(
                correlation_id=correlation_id,
                empresa_id=job.empresa_id,
                sync_job_id=job.id,
                source_config_id=job.source_config_id,
            ):
                source_config = session.scalar(
                    select(TenantSourceConfig).where(TenantSourceConfig.id == job.source_config_id)
                )
                if source_config is None:
                    self._mark_dead_letter(
                        session=session,
                        job=job,
                        empresa_id=job.empresa_id,
                        source_config=None,
                        error_message="source_config nao encontrado",
                    )
                    return 0

                try:
                    source_settings = resolve_runtime_settings(decrypt_json(source_config.settings_json))
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
                        chunk_size=self.chunk_size,
                    )
                    session.commit()
                    self.destination_dispatcher.dispatch_records(job.empresa_id, records)

                    now = datetime.now(UTC)
                    source_config.last_run_at = now
                    source_config.last_scheduled_at = now
                    source_config.next_run_at = now + timedelta(minutes=max(1, int(source_config.sync_interval_minutes)))
                    source_config.last_status = "ok"
                    source_config.last_error = None
                    job_repository.mark_done(job)
                    TenantAuditRepository(session).create(
                        empresa_id=job.empresa_id,
                        actor="tenant_sync_worker",
                        action="tenant.sync_job.completed",
                        resource_type="sync_job",
                        resource_id=job.id,
                        detail={
                            "source_config_id": job.source_config_id,
                            "inserted_count": str(inserted_count),
                            "updated_count": str(updated_count),
                            "correlation_id": correlation_id,
                        },
                    )
                    session.commit()
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
                    return 1
                except Exception as exc:
                    session.rollback()
                    source_config = session.scalar(
                        select(TenantSourceConfig).where(TenantSourceConfig.id == job.source_config_id)
                    )
                    policy = self._retry_policy(exc)
                    if source_config is not None:
                        source_config.last_status = (
                            "retrying" if job.attempts < policy["max_attempts"] else "dead_letter"
                        )
                        source_config.last_error = str(exc)
                    metrics_registry.record_tenant_queue_failed(job.empresa_id)
                    metrics_registry.record_sync_failure(job.empresa_id)
                    if job.attempts < policy["max_attempts"]:
                        backoff_minutes = min(
                            int(policy["base_backoff_minutes"]) * (2 ** max(0, job.attempts - 1)),
                            int(policy["max_backoff_minutes"]),
                        )
                        job_repository.mark_retry(job, str(exc), backoff_minutes=backoff_minutes)
                        TenantAuditRepository(session).create(
                            empresa_id=job.empresa_id,
                            actor="tenant_sync_worker",
                            action="tenant.sync_job.retry_scheduled",
                            resource_type="sync_job",
                            resource_id=job.id,
                            status="failure",
                            detail={
                                "source_config_id": job.source_config_id,
                                "failure_type": str(policy["failure_type"]),
                                "backoff_minutes": str(backoff_minutes),
                                "max_attempts": str(policy["max_attempts"]),
                                "error": str(exc),
                                "correlation_id": correlation_id,
                            },
                        )
                        session.commit()
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
                        TenantAuditRepository(session).create(
                            empresa_id=job.empresa_id,
                            actor="tenant_sync_worker",
                            action="tenant.sync_job.dead_letter",
                            resource_type="sync_job",
                            resource_id=job.id,
                            status="failure",
                            detail={
                                "source_config_id": job.source_config_id,
                                "failure_type": str(policy["failure_type"]),
                                "max_attempts": str(policy["max_attempts"]),
                                "error": str(exc),
                                "correlation_id": correlation_id,
                            },
                        )
                        session.commit()
                        metrics_registry.record_tenant_queue_dead_letter(job.empresa_id)
                        logger.exception(
                            "tenant_sync_job_dead_letter",
                            extra={"empresa_id": job.empresa_id, "job_id": job.id},
                        )
                    return 0

    def _retry_policy(self, error: Exception) -> dict[str, object]:
        failure_type = self._classify_failure(error)
        if failure_type == "permanent":
            return {
                "failure_type": failure_type,
                "max_attempts": 3,
                "base_backoff_minutes": 1,
                "max_backoff_minutes": 5,
            }
        if failure_type == "auth":
            return {
                "failure_type": failure_type,
                "max_attempts": 2,
                "base_backoff_minutes": 1,
                "max_backoff_minutes": 5,
            }
        return {
            "failure_type": "transient",
            "max_attempts": self.DEFAULT_MAX_ATTEMPTS,
            "base_backoff_minutes": self.BASE_BACKOFF_MINUTES,
            "max_backoff_minutes": 30,
        }

    @staticmethod
    def _classify_failure(error: Exception) -> str:
        message = str(error).lower()

        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code in (401, 403):
                return "auth"
            if 400 <= status_code < 500 and status_code not in (408, 429):
                return "permanent"
            return "transient"

        if isinstance(error, (httpx.TimeoutException, httpx.TransportError, OperationalError, OSError)):
            return "transient"

        if any(token in message for token in ("unauthorized", "forbidden", "token invalido", "api key")):
            return "auth"
        if any(
            token in message
            for token in (
                "nao informado",
                "inexistente",
                "nao suportado",
                "invalid",
                "malformed",
                "schema",
            )
        ):
            return "permanent"

        if any(
            token in message
            for token in (
                "timeout",
                "timed out",
                "connection",
                "temporar",
                "unavailable",
                "too many requests",
                str(http.HTTPStatus.TOO_MANY_REQUESTS),
            )
        ):
            return "transient"
        return "transient"

    def _mark_dead_letter(
        self,
        *,
        session,
        job,
        empresa_id: str,
        source_config: TenantSourceConfig | None,
        error_message: str,
    ) -> None:
        job_repository = TenantSyncJobRepository(session)
        job_repository.mark_dead_letter(job, error_message)
        if source_config is not None:
            source_config.last_status = "dead_letter"
            source_config.last_error = error_message
        TenantAuditRepository(session).create(
            empresa_id=empresa_id,
            actor="tenant_sync_worker",
            action="tenant.sync_job.dead_letter",
            resource_type="sync_job",
            resource_id=job.id,
            status="failure",
            detail={
                "source_config_id": job.source_config_id,
                "error": error_message,
            },
        )
        session.commit()

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

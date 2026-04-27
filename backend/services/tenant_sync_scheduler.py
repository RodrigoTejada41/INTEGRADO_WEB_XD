from __future__ import annotations

import logging
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.models.tenant_source_config import TenantSourceConfig
from backend.config.settings import get_settings
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.utils.correlation import bind_correlation_id, bind_log_context
from backend.utils.metrics import metrics_registry

logger = logging.getLogger(__name__)
settings = get_settings()


class TenantSyncScheduler:
    def __init__(self, session_factory: sessionmaker, scheduler: AsyncIOScheduler):
        self.session_factory = session_factory
        self.scheduler = scheduler

    def sync_all_jobs(self) -> None:
        with self.session_factory() as session:
            active_configs = list(
                session.scalars(
                    select(TenantSourceConfig).where(TenantSourceConfig.ativo.is_(True))
                ).all()
            )
            active_job_ids: set[str] = set()
            now = datetime.now(UTC)
            for config in active_configs:
                self._schedule_job(config)
                config.last_scheduled_at = now
                next_run_at = self._ensure_aware(config.next_run_at)
                if next_run_at is None or next_run_at < now:
                    config.next_run_at = now + timedelta(minutes=max(1, int(config.sync_interval_minutes)))
                active_job_ids.add(self._job_id(config.id))

            self._remove_stale_jobs(active_job_ids)
            session.commit()
            logger.info("tenant_sync_scheduler_reconciled", extra={"jobs": len(active_job_ids)})

    def _schedule_job(self, config: TenantSourceConfig) -> None:
        next_run_time = self._ensure_aware(config.next_run_at)
        self.scheduler.add_job(
            self.run_source_sync,
            trigger="interval",
            minutes=config.sync_interval_minutes,
            id=self._job_id(config.id),
            replace_existing=True,
            kwargs={"config_id": config.id},
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
            next_run_time=next_run_time,
        )

    def _remove_stale_jobs(self, active_job_ids: set[str]) -> None:
        for job in self.scheduler.get_jobs():
            if job.id.startswith("tenant-sync-") and job.id not in active_job_ids:
                self.scheduler.remove_job(job.id)

    @staticmethod
    def _job_id(config_id: str) -> str:
        return f"tenant-sync-{config_id}"

    def run_source_sync(self, config_id: str) -> None:
        correlation_id = f"sch-{uuid4()}"
        with bind_correlation_id(correlation_id), bind_log_context(correlation_id=correlation_id):
            self._run_source_sync_with_context(config_id)

    def _run_source_sync_with_context(self, config_id: str) -> None:
        with self.session_factory() as session:
            config = session.scalar(
                select(TenantSourceConfig).where(TenantSourceConfig.id == config_id)
            )
            if config is None or not config.ativo:
                metrics_registry.record_tenant_scheduler_failure()
                logger.warning("tenant_sync_config_not_found", extra={"config_id": config_id})
                return

            job_repository = TenantSyncJobRepository(session)
            now = datetime.now(UTC)
            correlation_id = f"job-{uuid4()}"
            pending_count = job_repository.get_pending_count_by_empresa_id(config.empresa_id)
            if pending_count >= settings.tenant_queue_max_pending_per_empresa:
                config.last_status = "backpressure"
                config.last_error = (
                    f"backpressure_ativa: pending={pending_count} "
                    f"limite={settings.tenant_queue_max_pending_per_empresa}"
                )
                config.last_scheduled_at = now
                config.next_run_at = now + timedelta(minutes=max(1, int(config.sync_interval_minutes)))
                session.commit()
                logger.warning(
                    "tenant_sync_job_skipped_backpressure",
                    extra={
                        "empresa_id": config.empresa_id,
                        "config_id": config.id,
                        "pending_count": pending_count,
                        "pending_limit": settings.tenant_queue_max_pending_per_empresa,
                    },
                )
                return

            payload = {
                "empresa_id": config.empresa_id,
                "source_config_id": config.id,
                "connector_type": config.connector_type,
                "correlation_id": correlation_id,
            }
            job_repository.create(
                job_id=str(uuid4()),
                empresa_id=config.empresa_id,
                source_config_id=config.id,
                payload_json=json.dumps(payload, ensure_ascii=False, sort_keys=True),
                scheduled_at=now,
            )
            config.last_scheduled_at = now
            config.next_run_at = now + timedelta(minutes=max(1, int(config.sync_interval_minutes)))
            session.commit()

        metrics_registry.record_tenant_scheduler_success(empresa_id=config.empresa_id)
        metrics_registry.record_tenant_queue_enqueue(1)
        logger.info(
            "tenant_sync_job_enqueued",
            extra={
                "empresa_id": config.empresa_id,
                "config_id": config_id,
                "interval_minutes": config.sync_interval_minutes,
                "correlation_id": correlation_id,
            },
        )

    @staticmethod
    def _ensure_aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

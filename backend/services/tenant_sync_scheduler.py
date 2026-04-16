from __future__ import annotations

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.models.tenant_source_config import TenantSourceConfig
from backend.utils.metrics import metrics_registry

logger = logging.getLogger(__name__)


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
            for config in active_configs:
                self._schedule_job(config)
                active_job_ids.add(self._job_id(config.id))

            self._remove_stale_jobs(active_job_ids)
            session.commit()
            logger.info("tenant_sync_scheduler_reconciled", extra={"jobs": len(active_job_ids)})

    def _schedule_job(self, config: TenantSourceConfig) -> None:
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
        )

    def _remove_stale_jobs(self, active_job_ids: set[str]) -> None:
        for job in self.scheduler.get_jobs():
            if job.id.startswith("tenant-sync-") and job.id not in active_job_ids:
                self.scheduler.remove_job(job.id)

    @staticmethod
    def _job_id(config_id: str) -> str:
        return f"tenant-sync-{config_id}"

    def run_source_sync(self, config_id: str) -> None:
        with self.session_factory() as session:
            config = session.scalar(
                select(TenantSourceConfig).where(TenantSourceConfig.id == config_id)
            )
            if config is None or not config.ativo:
                metrics_registry.record_tenant_scheduler_failure()
                logger.warning("tenant_sync_config_not_found", extra={"config_id": config_id})
                return

            config.last_run_at = datetime.now(UTC)
            config.last_status = "ok"
            config.last_error = None
            session.commit()

        metrics_registry.record_tenant_scheduler_success(empresa_id=config.empresa_id)
        logger.info(
            "tenant_sync_tick",
            extra={
                "empresa_id": config.empresa_id,
                "config_id": config_id,
                "interval_minutes": config.sync_interval_minutes,
            },
        )

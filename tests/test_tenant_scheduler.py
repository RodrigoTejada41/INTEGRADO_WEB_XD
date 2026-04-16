from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler


def test_tenant_scheduler_creates_jobs_and_updates_heartbeat() -> None:
    db_path = Path("output/test_tenant_scheduler.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    for module_name in [
        "backend.main",
        "backend.config.database",
        "backend.config.settings",
        "backend.services.tenant_sync_scheduler",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal
    from backend.config.database import engine
    from backend.models import Base
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.repositories.tenant_config_repository import TenantConfigRepository
    from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.services.tenant_sync_worker import TenantSyncWorker

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa Scheduler",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        config = source_repository.create(
            config_id="11111111-1111-1111-1111-111111111111",
            empresa_id="12345678000199",
            nome="Fonte principal",
            connector_type="mariadb",
            sync_interval_minutes=30,
            settings_json='{"database":"xd","host":"127.0.0.1","port":"3308"}',
        )
        session.commit()

    scheduler = AsyncIOScheduler(timezone="UTC")
    tenant_scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=scheduler)
    tenant_scheduler._schedule_job(config)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == f"tenant-sync-{config.id}"
    assert jobs[0].trigger.interval.total_seconds() == 30 * 60

    tenant_scheduler.run_source_sync(config.id)

    with SessionLocal() as session:
        job_repository = TenantSyncJobRepository(session)
        pending_jobs = job_repository.list_pending()
        assert len(pending_jobs) == 1
        assert pending_jobs[0].source_config_id == config.id

    worker = TenantSyncWorker(session_factory=SessionLocal)
    processed = worker.drain_pending_jobs()
    assert processed == 1

    with SessionLocal() as session:
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_status == "ok"
        assert config.last_run_at is not None
        assert len(TenantSyncJobRepository(session).list_pending()) == 0

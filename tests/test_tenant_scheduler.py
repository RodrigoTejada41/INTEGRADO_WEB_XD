from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text


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
        "backend.api.routes",
        "backend.api.routes.tenant_admin",
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
    from backend.models.venda import Venda
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.repositories.tenant_config_repository import TenantConfigRepository
    from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.services.tenant_sync_worker import TenantSyncWorker
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    source_db_path = Path("output/test_tenant_scheduler_source.db")
    if source_db_path.exists():
        source_db_path.unlink()
    source_engine = create_engine(f"sqlite+pysqlite:///{source_db_path.as_posix()}", future=True)
    with source_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE vendas (
                    uuid TEXT PRIMARY KEY,
                    empresa_id TEXT NOT NULL,
                    produto TEXT NOT NULL,
                    valor NUMERIC NOT NULL,
                    data DATE NOT NULL,
                    data_atualizacao TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO vendas (uuid, empresa_id, produto, valor, data, data_atualizacao)
                VALUES (:uuid, :empresa_id, :produto, :valor, :data, :data_atualizacao)
                """
            ),
            [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "empresa_id": "12345678000199",
                    "produto": "Produto origem",
                    "valor": "100.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T13:00:00+00:00",
                }
            ],
        )

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
            settings_json=encrypt_json(
                {
                    "mariadb_url": f"sqlite+pysqlite:///{source_db_path.as_posix()}",
                    "batch_size": "100",
                    "database": "xd",
                    "host": "127.0.0.1",
                    "port": "3308",
                }
            ),
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
        venda = session.get(Venda, 1)
        assert venda is not None
        assert venda.empresa_id == "12345678000199"
        assert venda.produto == "Produto origem"


def test_tenant_sync_job_retries_and_moves_to_dead_letter() -> None:
    db_path = Path("output/test_tenant_dead_letter.db")
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
    from backend.models.tenant_sync_job import TenantSyncJob
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.repositories.tenant_config_repository import TenantConfigRepository
    from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.services.tenant_sync_worker import TenantSyncWorker
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa DLQ",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        config = source_repository.create(
            config_id="22222222-2222-2222-2222-222222222222",
            empresa_id="12345678000199",
            nome="Fonte invalida",
            connector_type="file",
            sync_interval_minutes=15,
            settings_json=encrypt_json(
                {
                    "path": "output/arquivo_inexistente.json",
                    "batch_size": "10",
                }
            ),
        )
        session.commit()

    tenant_scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=AsyncIOScheduler(timezone="UTC"))
    tenant_scheduler.run_source_sync(config.id)

    worker = TenantSyncWorker(session_factory=SessionLocal)

    processed = worker.drain_pending_jobs()
    assert processed == 0

    with SessionLocal() as session:
        job_repository = TenantSyncJobRepository(session)
        job = session.execute(select(TenantSyncJob)).scalar_one()
        assert job.status == "pending"
        assert job.attempts == 1
        job.next_run_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    processed = worker.drain_pending_jobs()
    assert processed == 0

    with SessionLocal() as session:
        job = session.execute(select(TenantSyncJob)).scalar_one()
        assert job.status == "pending"
        assert job.attempts == 2
        job.next_run_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    processed = worker.drain_pending_jobs()
    assert processed == 0

    with SessionLocal() as session:
        job = session.execute(select(TenantSyncJob)).scalar_one()
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_status == "dead_letter"
        assert config.last_error is not None
        assert job.status == "dead_letter"
        assert job.attempts == 3
        assert job.dead_letter_reason is not None
        assert len(TenantSyncJobRepository(session).list_pending()) == 0

    from backend.main import app

    with TestClient(app) as client:
        summary_resp = client.get(
            f"/admin/tenants/{config.empresa_id}/sync-jobs/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert summary_resp.status_code == 200, summary_resp.text
        assert summary_resp.json()["dead_letter_count"] == 1
        assert summary_resp.json()["pending_count"] == 0

        dlq_resp = client.get(
            f"/admin/tenants/{config.empresa_id}/sync-jobs/dead-letter",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert dlq_resp.status_code == 200, dlq_resp.text
        assert len(dlq_resp.json()) == 1
        job_id = dlq_resp.json()[0]["id"]

        retry_resp = client.post(
            f"/admin/tenants/{config.empresa_id}/sync-jobs/{job_id}/retry",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert retry_resp.status_code == 200, retry_resp.text
        assert retry_resp.json()["status"] == "pending"

        summary_after_retry = client.get(
            f"/admin/tenants/{config.empresa_id}/sync-jobs/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert summary_after_retry.status_code == 200, summary_after_retry.text
        assert summary_after_retry.json()["pending_count"] == 1
        assert summary_after_retry.json()["dead_letter_count"] == 0

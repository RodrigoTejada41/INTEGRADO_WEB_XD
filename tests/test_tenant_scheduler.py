from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker


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
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_scheduled_at is not None
        assert config.next_run_at is not None
        assert config.next_run_at > config.last_scheduled_at
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


def test_tenant_worker_pool_processes_multiple_jobs() -> None:
    db_path = Path("output/test_tenant_worker_pool.db")
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
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    source_db_path = Path("output/test_tenant_worker_pool_source.db")
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
                    "uuid": "44444444-4444-4444-4444-444444444441",
                    "empresa_id": "12345678000199",
                    "produto": "Produto 1",
                    "valor": "10.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T10:00:00+00:00",
                },
                {
                    "uuid": "44444444-4444-4444-4444-444444444442",
                    "empresa_id": "12345678000199",
                    "produto": "Produto 2",
                    "valor": "20.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T10:05:00+00:00",
                },
            ],
        )

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa Pool",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        config = source_repository.create(
            config_id="55555555-5555-5555-5555-555555555555",
            empresa_id="12345678000199",
            nome="Fonte pool",
            connector_type="mariadb",
            sync_interval_minutes=15,
            settings_json=encrypt_json(
                {
                    "mariadb_url": f"sqlite+pysqlite:///{source_db_path.as_posix()}",
                    "batch_size": "50",
                }
            ),
        )
        session.commit()

    tenant_scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=AsyncIOScheduler(timezone="UTC"))
    tenant_scheduler.run_source_sync(config.id)
    tenant_scheduler.run_source_sync(config.id)

    worker = TenantSyncWorker(session_factory=SessionLocal, max_workers=2)
    processed = worker.drain_pending_jobs(limit=10, max_workers=2)
    assert processed == 2

    with SessionLocal() as session:
        job_repository = TenantSyncJobRepository(session)
        assert len(job_repository.list_pending()) == 0
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_status == "ok"


def test_crypto_uses_encryption_key_file() -> None:
    key_file = Path("output/test_tenant_crypto.key")
    key = Fernet.generate_key().decode("utf-8")
    key_file.write_text(key, encoding="utf-8")

    os.environ["TENANT_CONFIG_ENCRYPTION_KEY_FILE"] = str(key_file)

    import backend.config.settings as settings_module
    from backend.utils import crypto as crypto_module

    settings_module.get_settings.cache_clear()
    crypto_module.get_fernet.cache_clear()

    ciphertext = crypto_module.encrypt_text("segredo")
    assert crypto_module.decrypt_text(ciphertext) == "segredo"

    os.environ.pop("TENANT_CONFIG_ENCRYPTION_KEY_FILE", None)
    settings_module.get_settings.cache_clear()
    crypto_module.get_fernet.cache_clear()


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
    from backend.models.tenant_destination_config import TenantDestinationConfig
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
        assert job.status == "dead_letter"
        assert job.attempts == 1
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_status == "dead_letter"
        assert config.last_error is not None
        assert job.status == "dead_letter"
        assert job.attempts == 1
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


def test_tenant_sync_worker_delivers_to_destination_database() -> None:
    db_path = Path("output/test_tenant_destination_delivery.db")
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
    from backend.models.tenant_destination_config import TenantDestinationConfig
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.repositories.tenant_config_repository import TenantConfigRepository
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.services.tenant_sync_worker import TenantSyncWorker
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    source_db_path = Path("output/test_tenant_destination_source.db")
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
                    "uuid": "33333333-3333-3333-3333-333333333333",
                    "empresa_id": "12345678000199",
                    "produto": "Produto destino",
                    "valor": "150.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T14:00:00+00:00",
                }
            ],
        )

    destination_db_path = Path("output/test_tenant_destination_target.db")
    if destination_db_path.exists():
        destination_db_path.unlink()
    destination_engine = create_engine(f"sqlite+pysqlite:///{destination_db_path.as_posix()}", future=True)
    Base.metadata.create_all(bind=destination_engine)

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa Destino",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        source_config = source_repository.create(
            config_id="33333333-3333-3333-3333-333333333333",
            empresa_id="12345678000199",
            nome="Fonte destino",
            connector_type="mariadb",
            sync_interval_minutes=15,
            settings_json=encrypt_json(
                {
                    "mariadb_url": f"sqlite+pysqlite:///{source_db_path.as_posix()}",
                    "batch_size": "50",
                }
            ),
        )
        destination_repository = TenantConfigRepository(session, TenantDestinationConfig)
        destination_repository.create(
            config_id="44444444-4444-4444-4444-444444444444",
            empresa_id="12345678000199",
            nome="Destino central",
            connector_type="postgresql",
            sync_interval_minutes=15,
            settings_json=encrypt_json(
                {
                    "database_url": f"sqlite+pysqlite:///{destination_db_path.as_posix()}",
                }
            ),
        )
        session.commit()

    tenant_scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=AsyncIOScheduler(timezone="UTC"))
    tenant_scheduler.run_source_sync(source_config.id)

    worker = TenantSyncWorker(session_factory=SessionLocal)
    processed = worker.drain_pending_jobs()
    assert processed == 1

    with SessionLocal() as session:
        source_config = session.get(TenantSourceConfig, source_config.id)
        destination_config = session.get(TenantDestinationConfig, "44444444-4444-4444-4444-444444444444")
        venda_central = session.get(Venda, 1)
        assert source_config is not None
        assert destination_config is not None
        assert source_config.last_status == "ok"
        assert destination_config.last_status == "ok"
        assert venda_central is not None
        assert venda_central.produto == "Produto destino"

    destination_session_factory = sessionmaker(bind=destination_engine, autoflush=False, autocommit=False, future=True)
    with destination_session_factory() as destination_session:
        venda_destino = destination_session.get(Venda, 1)
        assert venda_destino is not None
        assert venda_destino.empresa_id == "12345678000199"
        assert venda_destino.produto == "Produto destino"


def test_tenant_queue_backpressure_selection_is_fair_per_empresa() -> None:
    db_path = Path("output/test_tenant_backpressure_fair.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    for module_name in [
        "backend.config.database",
        "backend.config.settings",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal, engine
    from backend.models import Base
    from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository

    Base.metadata.create_all(bind=engine)

    now = datetime.now(UTC) - timedelta(seconds=1)
    with SessionLocal() as session:
        repository = TenantSyncJobRepository(session)
        for idx in range(4):
            repository.create(
                job_id=f"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa{idx:02d}",
                empresa_id="11111111000101",
                source_config_id="source-a",
                payload_json="{}",
                scheduled_at=now,
            )
        for idx in range(2):
            repository.create(
                job_id=f"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb{idx:02d}",
                empresa_id="22222222000102",
                source_config_id="source-b",
                payload_json="{}",
                scheduled_at=now,
            )
        session.commit()

    with SessionLocal() as session:
        repository = TenantSyncJobRepository(session)
        selected = repository.list_pending_with_backpressure(limit=10, per_tenant_limit=1)
        assert len(selected) == 2
        assert {job.empresa_id for job in selected} == {"11111111000101", "22222222000102"}

        selected_2 = repository.list_pending_with_backpressure(limit=10, per_tenant_limit=2)
        assert len(selected_2) == 4
        counts: dict[str, int] = {}
        for job in selected_2:
            counts[job.empresa_id] = counts.get(job.empresa_id, 0) + 1
        assert counts["11111111000101"] == 2
        assert counts["22222222000102"] == 2


def test_tenant_sync_job_transient_failure_schedules_retry() -> None:
    db_path = Path("output/test_tenant_transient_retry.db")
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
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.services.tenant_sync_worker import TenantSyncWorker
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa Retry",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        config = source_repository.create(
            config_id="77777777-7777-7777-7777-777777777777",
            empresa_id="12345678000199",
            nome="Fonte API offline",
            connector_type="api",
            sync_interval_minutes=15,
            settings_json=encrypt_json(
                {
                    "base_url": "http://127.0.0.1:9",
                    "endpoint": "/records",
                    "timeout_seconds": "1",
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
        job = session.execute(select(TenantSyncJob)).scalar_one()
        config = session.get(TenantSourceConfig, config.id)
        assert config is not None
        assert config.last_status == "retrying"
        assert job.status == "pending"
        assert job.attempts == 1
        assert job.next_run_at.timestamp() > datetime.now(UTC).timestamp()


def test_tenant_scheduler_applies_enqueue_backpressure_limit() -> None:
    db_path = Path("output/test_tenant_scheduler_backpressure_limit.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["TENANT_QUEUE_MAX_PENDING_PER_EMPRESA"] = "1"

    for module_name in [
        "backend.config.database",
        "backend.config.settings",
        "backend.services.tenant_sync_scheduler",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal, engine
    from backend.models import Base
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.repositories.tenant_config_repository import TenantConfigRepository
    from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
    from backend.repositories.tenant_repository import TenantRepository
    from backend.services.tenant_sync_scheduler import TenantSyncScheduler
    from backend.utils.crypto import encrypt_json

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        tenant_repository = TenantRepository(session)
        tenant_repository.upsert_tenant(
            empresa_id="12345678000199",
            nome="Empresa BP",
            api_key_hash="hash",
        )
        source_repository = TenantConfigRepository(session, TenantSourceConfig)
        config = source_repository.create(
            config_id="99999999-9999-9999-9999-999999999999",
            empresa_id="12345678000199",
            nome="Fonte BP",
            connector_type="file",
            sync_interval_minutes=15,
            settings_json=encrypt_json({"path": "output/arquivo_inexistente.json"}),
        )
        session.commit()

    scheduler = TenantSyncScheduler(session_factory=SessionLocal, scheduler=AsyncIOScheduler(timezone="UTC"))
    scheduler.run_source_sync(config.id)
    scheduler.run_source_sync(config.id)

    with SessionLocal() as session:
        repository = TenantSyncJobRepository(session)
        pending_jobs = repository.list_pending(limit=10)
        config = session.get(TenantSourceConfig, config.id)
        assert len(pending_jobs) == 1
        assert config is not None
        assert config.last_status == "backpressure"
        assert config.last_error is not None

    os.environ.pop("TENANT_QUEUE_MAX_PENDING_PER_EMPRESA", None)

from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

def test_sync_route_records_audit_event() -> None:
    db_path = Path("output/test_backend_audit.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    for module_name in [
        "backend.main",
        "backend.api.deps",
        "backend.api.routes",
        "backend.api.routes.sync",
        "backend.api.routes.tenant_admin",
        "backend.config.database",
        "backend.config.settings",
        "backend.services.sync_service",
        "backend.utils.metrics",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal
    from backend.config.database import engine
    from backend.main import app
    from backend.models import Base
    from backend.models.tenant_audit_event import TenantAuditEvent

    Base.metadata.create_all(bind=engine)

    payload = {
        "empresa_id": "12345678000199",
        "records": [
            {
                "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "produto": "Produto auditado",
                "valor": "9.90",
                "data": "2026-04-16",
                "data_atualizacao": "2026-04-16T12:00:00+00:00",
            }
        ],
    }

    with TestClient(app) as client:
        provision_resp = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"},
            json={"empresa_id": "12345678000199", "nome": "Empresa Audit"},
        )
        assert provision_resp.status_code == 200, provision_resp.text
        assert provision_resp.json()["api_key_expires_at"]
        raw_key = provision_resp.json()["api_key"]

        response = client.post(
            "/sync",
            headers={
                "X-API-Key": raw_key,
                "X-Empresa-Id": "12345678000199",
                "X-Correlation-Id": "corr-test-123",
                "User-Agent": "pytest-suite",
            },
            json=payload,
        )
        assert response.status_code == 200, response.text

    with SessionLocal() as session:
        events = session.query(TenantAuditEvent).all()
        assert len(events) == 2
        actions = {event.action for event in events}
        assert "tenant.provision" in actions
        assert "sync.ingest" in actions
        assert all(event.empresa_id == "12345678000199" for event in events)
        sync_event = next(event for event in events if event.action == "sync.ingest")
        assert sync_event.correlation_id == "corr-test-123"
        assert sync_event.request_path == "/sync"
        assert sync_event.user_agent == "pytest-suite"
        assert '"correlation_id": "corr-test-123"' in sync_event.detail_json


def test_admin_tenant_observability_endpoint() -> None:
    db_path = Path("output/test_backend_observability.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    for module_name in [
        "backend.main",
        "backend.api.deps",
        "backend.api.routes",
        "backend.api.routes.sync",
        "backend.api.routes.tenant_admin",
        "backend.config.database",
        "backend.config.settings",
        "backend.services.sync_service",
        "backend.utils.metrics",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import engine
    from backend.main import app
    from backend.models import Base

    Base.metadata.create_all(bind=engine)

    payload = {
        "empresa_id": "12345678000199",
        "records": [
            {
                "uuid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "produto": "Produto observability",
                "valor": "11.00",
                "data": "2026-04-16",
                "data_atualizacao": "2026-04-16T12:00:00+00:00",
            }
        ],
    }

    with TestClient(app) as client:
        provision_resp = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test"},
            json={"empresa_id": "12345678000199", "nome": "Empresa Obs"},
        )
        assert provision_resp.status_code == 200, provision_resp.text
        raw_key = provision_resp.json()["api_key"]

        sync_resp = client.post(
            "/sync",
            headers={
                "X-API-Key": raw_key,
                "X-Empresa-Id": "12345678000199",
                "X-Correlation-Id": "corr-obs-123",
            },
            json=payload,
        )
        assert sync_resp.status_code == 200, sync_resp.text

        observability_resp = client.get(
            "/admin/tenants/12345678000199/observability",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert observability_resp.status_code == 200, observability_resp.text
        body = observability_resp.json()
        assert body["empresa_id"] == "12345678000199"
        assert body["sync_batches_total"] >= 1
        assert "tenant_queue_processed_total" in body
        assert "sync_last_success_lag_seconds" in body


def test_expired_tenant_key_is_rejected() -> None:
    db_path = Path("output/test_backend_expired_key.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    for module_name in [
        "backend.main",
        "backend.api.deps",
        "backend.api.routes",
        "backend.api.routes.sync",
        "backend.api.routes.tenant_admin",
        "backend.config.database",
        "backend.config.settings",
        "backend.services.sync_service",
        "backend.utils.metrics",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal
    from backend.config.database import engine
    from backend.main import app
    from backend.models import Base
    from backend.models.tenant import Tenant

    Base.metadata.create_all(bind=engine)

    payload = {
        "empresa_id": "12345678000199",
        "records": [
            {
                "uuid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "produto": "Produto expirado",
                "valor": "21.00",
                "data": "2026-04-16",
                "data_atualizacao": "2026-04-16T12:00:00+00:00",
            }
        ],
    }

    with TestClient(app) as client:
        provision_resp = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test"},
            json={"empresa_id": "12345678000199", "nome": "Empresa Expirada"},
        )
        assert provision_resp.status_code == 200, provision_resp.text
        raw_key = provision_resp.json()["api_key"]

        with SessionLocal() as session:
            tenant = session.get(Tenant, "12345678000199")
            assert tenant is not None
            tenant.api_key_expires_at = datetime.now(UTC) - timedelta(minutes=1)
            session.commit()

        response = client.post(
            "/sync",
            headers={
                "X-API-Key": raw_key,
                "X-Empresa-Id": "12345678000199",
            },
            json=payload,
        )
        assert response.status_code == 401, response.text
        assert response.json()["detail"] == "Credenciais expiradas."

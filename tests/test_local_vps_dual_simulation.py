from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


def _reset_backend_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "backend.connectors" or module_name.startswith("backend.connectors."):
            continue
        if module_name == "backend" or module_name.startswith("backend."):
            sys.modules.pop(module_name, None)


def _reset_sync_admin_modules() -> None:
    prefixes = ("app",)
    for module_name in list(sys.modules):
        if module_name == "app" or any(module_name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(module_name, None)


def _prepare_backend(db_name: str) -> None:
    db_path = Path("output") / db_name
    if db_path.exists():
        db_path.unlink()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "backend-admin-token"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"
    os.environ["ENVIRONMENT"] = "development"

    _reset_backend_modules()
    importlib.invalidate_caches()


def _prepare_sync_admin(db_name: str) -> None:
    db_path = Path("output") / db_name
    if db_path.exists():
        db_path.unlink()
    for suffix in ("-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.exists():
            sidecar.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "sync-admin-test-secret"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["CONTROL_API_BASE_URL"] = "http://vps.local"
    os.environ["CONTROL_ADMIN_TOKEN"] = "backend-admin-token"
    os.environ["CONTROL_EMPRESA_ID"] = "12345678000199"
    os.environ["CONTROL_EMPRESA_NOME"] = "Empresa VPS"
    os.environ["AGENT_API_KEY_FILE"] = "output/test_local_vps_dual_simulation.agent.key"
    os.environ["AGENT_AUDIT_FILE"] = "output/test_local_vps_dual_simulation.agent.audit.log"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = "output/test_local_vps_dual_simulation.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))

    _reset_sync_admin_modules()
    importlib.invalidate_caches()


class _FakeHttpxClient:
    def __init__(self, backend_client: TestClient, *_args, **_kwargs) -> None:
        self._backend_client = backend_client

    def __enter__(self) -> "_FakeHttpxClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        json: object | None = None,
        data: object | None = None,
        **_kwargs,
    ):
        path = urlparse(str(url)).path or "/"
        return self._backend_client.request(
            method=method,
            url=path,
            headers=headers,
            params=params,
            json=json,
            data=data,
        )

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)


def test_local_admin_panel_can_simulate_vps_control_flow(monkeypatch) -> None:
    _prepare_backend("test_local_vps_backend.db")
    from backend.main import app as backend_app
    from backend.config.database import SessionLocal as BackendSessionLocal
    from backend.models.local_client import LocalClient
    from backend.models.local_client_log import LocalClientLog
    from backend.models.tenant_audit_event import TenantAuditEvent

    _prepare_sync_admin("test_local_vps_sync_admin.db")
    from app.main import app as sync_admin_app
    from app.services import control_service as control_service_module

    backend_client = TestClient(backend_app)

    def fake_httpx_client(*args, **kwargs):
        return _FakeHttpxClient(backend_client, *args, **kwargs)

    monkeypatch.setattr(control_service_module.httpx, "Client", fake_httpx_client)

    empresa_id = "12345678000199"
    client_id = "local-agent-vps-001"
    initial_api_key = ""
    rotated_api_key = ""
    key_file = Path("output/test_local_vps_dual_simulation.agent.key")

    with backend_client, TestClient(sync_admin_app) as sync_client:
        login_resp = sync_client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303), login_resp.text

        provision_resp = sync_client.post(
            "/settings/provision-tenant",
            data={"empresa_id": empresa_id, "nome": "Empresa VPS"},
            follow_redirects=False,
        )
        assert provision_resp.status_code in (302, 303), provision_resp.text

        provision_location = parse_qs(urlparse(provision_resp.headers["location"]).query)
        assert "Tenant provisionado e chave aplicada no agente" in provision_location["flash"][0]
        assert key_file.exists()
        initial_api_key = key_file.read_text(encoding="utf-8").strip()
        assert provision_location["generated_key"][0] == initial_api_key

        register_resp = backend_client.post(
            "/api/v1/register",
            headers={
                "X-Empresa-Id": empresa_id,
                "X-API-Key": initial_api_key,
                "X-Correlation-Id": "corr-local-vps-register",
            },
            json={
                "client_id": client_id,
                "hostname": "agent-local-vps",
                "ip": "10.10.0.10",
                "endpoint_url": "http://agent-local-vps.local/api",
                "token": "local-control-token-vps-abcdefghijklmnopqrstuvwxyz",
                "token_expires_at": "2026-05-01T08:00:00+00:00",
                "config_snapshot": {"sync_interval_minutes": 16},
                "status_snapshot": {"last_sync_at": "2026-04-24T08:00:00+00:00"},
            },
        )
        assert register_resp.status_code == 200, register_resp.text
        assert register_resp.json()["status"] == "registered"

        connected_page = sync_client.get("/connected-apis")
        assert connected_page.status_code == 200, connected_page.text
        assert "APIs Conectadas" in connected_page.text
        assert empresa_id in connected_page.text
        assert "Empresa VPS" in connected_page.text
        assert "agent-local-vps" in connected_page.text

        detail_page = sync_client.get(f"/connected-apis/{client_id}")
        assert detail_page.status_code == 200, detail_page.text
        assert "Forcar sincronizacao" in detail_page.text
        assert "Empresa VPS" in detail_page.text

        sync_insert_resp = backend_client.post(
            "/sync",
            headers={
                "X-Empresa-Id": empresa_id,
                "X-API-Key": initial_api_key,
                "X-Correlation-Id": "corr-local-vps-sync-insert",
            },
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "33333333-3333-3333-3333-333333333333",
                        "produto": "Produto VPS",
                        "valor": "90.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:10:00Z",
                    }
                ],
            },
        )
        assert sync_insert_resp.status_code == 200, sync_insert_resp.text
        assert sync_insert_resp.json()["inserted_count"] == 1
        assert sync_insert_resp.json()["updated_count"] == 0

        rotate_resp = sync_client.post(
            "/settings/rotate-tenant-key",
            data={"empresa_id": empresa_id},
            follow_redirects=False,
        )
        assert rotate_resp.status_code in (302, 303), rotate_resp.text

        rotate_location = parse_qs(urlparse(rotate_resp.headers["location"]).query)
        assert "Chave rotacionada e aplicada no agente" in rotate_location["flash"][0]
        rotated_api_key = key_file.read_text(encoding="utf-8").strip()
        assert rotated_api_key
        assert rotated_api_key != initial_api_key
        assert rotate_location["generated_key"][0] == rotated_api_key

        old_key_resp = backend_client.post(
            "/sync",
            headers={
                "X-Empresa-Id": empresa_id,
                "X-API-Key": initial_api_key,
                "X-Correlation-Id": "corr-local-vps-old-key",
            },
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "33333333-3333-3333-3333-333333333333",
                        "produto": "Produto VPS Bloqueado",
                        "valor": "99.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:20:00Z",
                    }
                ],
            },
        )
        assert old_key_resp.status_code == 401, old_key_resp.text

        new_key_resp = backend_client.post(
            "/sync",
            headers={
                "X-Empresa-Id": empresa_id,
                "X-API-Key": rotated_api_key,
                "X-Correlation-Id": "corr-local-vps-new-key",
            },
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "33333333-3333-3333-3333-333333333333",
                        "produto": "Produto VPS Atualizado",
                        "valor": "120.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:30:00Z",
                    }
                ],
            },
        )
        assert new_key_resp.status_code == 200, new_key_resp.text
        assert new_key_resp.json()["updated_count"] == 1

        clients_summary = backend_client.get(
            "/api/v1/clients/summary",
            headers={"X-Admin-Token": "backend-admin-token"},
        )
        assert clients_summary.status_code == 200, clients_summary.text
        assert clients_summary.json()["total_clients"] == 1
        assert clients_summary.json()["online_clients"] == 1

    with BackendSessionLocal() as session:
        tenant_audits = list(
            session.query(TenantAuditEvent)
            .filter(TenantAuditEvent.empresa_id == empresa_id)
            .order_by(TenantAuditEvent.created_at.asc())
            .all()
        )
        local_clients = list(
            session.query(LocalClient)
            .filter(LocalClient.empresa_id == empresa_id)
            .order_by(LocalClient.created_at.asc())
            .all()
        )

    assert any(audit.action == "tenant.provision" for audit in tenant_audits)
    assert any(audit.action == "tenant.rotate_key" for audit in tenant_audits)
    assert any(audit.action == "sync.ingest" for audit in tenant_audits)
    assert any(audit.correlation_id == "corr-local-vps-sync-insert" for audit in tenant_audits)
    assert any(audit.correlation_id == "corr-local-vps-new-key" for audit in tenant_audits)

    assert any(client.id == client_id for client in local_clients)
    local_client_logs = list(
        session.query(LocalClientLog)
        .filter(LocalClientLog.empresa_id == empresa_id)
        .order_by(LocalClientLog.created_at.asc())
        .all()
    )
    assert any(log.event_type == "client.register" for log in local_client_logs)
    assert any("corr-local-vps-register" in log.detail_json for log in local_client_logs)

    _reset_sync_admin_modules()
    _reset_backend_modules()
    importlib.invalidate_caches()

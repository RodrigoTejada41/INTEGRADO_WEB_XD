from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin() -> None:
    db_path = Path("output/test_sync_admin_connected_apis.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = "output/test_sync_admin_connected_apis_token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_web_lists_and_controls_connected_apis(monkeypatch) -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService, RemoteClientFleetSummary

    def fake_fetch_remote_client_summary(self, **kwargs):
        return RemoteClientFleetSummary(total_clients=2, online_clients=1, error_clients=1, unique_empresas=2)

    def fake_fetch_remote_clients(self, **kwargs):
        return [
            {
                "id": "client-a",
                "empresa_id": "12345678000199",
                "empresa_nome": "Empresa Alpha",
                "hostname": "host-a",
                "status": "online",
                "endpoint_url": "https://host-a.local/api",
                "last_sync_at": "2026-04-20T10:00:00+00:00",
                "last_command_poll_at": "2026-04-20T10:01:00+00:00",
            },
            {
                "id": "client-b",
                "empresa_id": "98765432000155",
                "empresa_nome": "Empresa Beta",
                "hostname": "host-b",
                "status": "error",
                "endpoint_url": "https://host-b.local/api",
                "last_sync_at": "2026-04-20T09:00:00+00:00",
                "last_command_poll_at": "2026-04-20T09:01:00+00:00",
            },
        ]

    def fake_fetch_remote_client(self, client_id: str):
        return {
            "id": client_id,
            "empresa_id": "12345678000199",
            "empresa_nome": "Empresa Alpha",
            "hostname": "host-a",
            "status": "online",
            "endpoint_url": "https://host-a.local/api",
            "last_seen_at": "2026-04-20T10:05:00+00:00",
            "last_sync_at": "2026-04-20T10:00:00+00:00",
            "last_command_poll_at": "2026-04-20T10:01:00+00:00",
            "config_snapshot": {"sync_interval_minutes": 15},
            "status_snapshot": {"last_sync_status": "success"},
        }

    def fake_fetch_remote_client_logs(self, client_id: str, **kwargs):
        return [
            {
                "created_at": "2026-04-20T10:01:00+00:00",
                "event_type": "commands.pull",
                "status": "success",
                "correlation_id": "corr-123",
                "detail": {"commands_count": 1},
            }
        ]

    queue_calls: list[tuple[str, dict | None]] = []

    def fake_queue_remote_force_sync(self, client_id: str, *, actor: str | None = None):
        queue_calls.append((client_id, {"actor": actor, "action": "sync"}))
        return {"status": "queued"}

    def fake_queue_remote_config_update(self, client_id: str, *, payload: dict[str, object], actor: str | None = None):
        queue_calls.append((client_id, {"actor": actor, "action": "config", "payload": payload}))
        return {"status": "queued"}

    monkeypatch.setattr(ControlService, "fetch_remote_client_summary", fake_fetch_remote_client_summary)
    monkeypatch.setattr(ControlService, "fetch_remote_clients", fake_fetch_remote_clients)
    monkeypatch.setattr(ControlService, "fetch_remote_client", fake_fetch_remote_client)
    monkeypatch.setattr(ControlService, "fetch_remote_client_logs", fake_fetch_remote_client_logs)
    monkeypatch.setattr(ControlService, "queue_remote_force_sync", fake_queue_remote_force_sync)
    monkeypatch.setattr(ControlService, "queue_remote_config_update", fake_queue_remote_config_update)

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        fleet_page = client.get("/connected-apis")
        assert fleet_page.status_code == 200
        assert "APIs Conectadas" in fleet_page.text
        assert "Total" in fleet_page.text
        assert "Online" in fleet_page.text
        assert "Offline" in fleet_page.text
        assert "Erro" in fleet_page.text
        assert "Empresas distintas: 2" in fleet_page.text
        assert "host-a" in fleet_page.text
        assert "host-b" in fleet_page.text
        assert "Empresa Alpha" in fleet_page.text
        assert "/reports?empresa_id=12345678000199" in fleet_page.text

        detail_page = client.get("/connected-apis/client-a")
        assert detail_page.status_code == 200
        assert "Saude operacional" in detail_page.text
        assert "Sync e poll fora da janela esperada" in detail_page.text
        assert "Ultimo evento" in detail_page.text
        assert "Forcar sincronizacao" in detail_page.text
        assert "corr-123" in detail_page.text
        assert "Empresa Alpha" in detail_page.text
        assert "/reports?empresa_id=12345678000199" in detail_page.text

        sync_action = client.post("/connected-apis/client-a/sync", follow_redirects=False)
        assert sync_action.status_code in (302, 303)

        config_action = client.post(
            "/connected-apis/client-a/config",
            data={"config_payload": '{"sync_interval_minutes": 10}'},
            follow_redirects=False,
        )
        assert config_action.status_code in (302, 303)

    assert queue_calls[0][0] == "client-a"
    assert queue_calls[0][1]["action"] == "sync"
    assert queue_calls[1][1]["action"] == "config"
    assert queue_calls[1][1]["payload"]["sync_interval_minutes"] == 10

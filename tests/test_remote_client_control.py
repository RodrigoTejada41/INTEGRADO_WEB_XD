from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _reset_backend_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "backend.main" or module_name.startswith(("backend.api", "backend.config", "backend.services")):
            sys.modules.pop(module_name, None)


def test_remote_client_registration_and_command_flow() -> None:
    db_path = Path("output/test_remote_client_control.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.config.database import SessionLocal
    from backend.main import app
    from backend.models.local_client_command import LocalClientCommand
    from backend.models.local_client_log import LocalClientLog

    with TestClient(app) as client:
        tenant_resp = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"},
            json={"empresa_id": "12345678000199", "nome": "Empresa Remota"},
        )
        assert tenant_resp.status_code == 200, tenant_resp.text
        tenant_api_key = tenant_resp.json()["api_key"]

        register_resp = client.post(
            "/api/v1/register",
            headers={
                "X-Empresa-Id": "12345678000199",
                "X-API-Key": tenant_api_key,
                "X-Correlation-Id": "corr-registration-001",
            },
            json={
                "client_id": "client-local-001",
                "hostname": "host-local",
                "ip": "10.0.0.10",
                "endpoint_url": "https://local.example/api",
                "token": "local-control-token-abcdefghijklmnopqrstuvwxyz12",
                "config_snapshot": {"sync_interval_minutes": 15},
                "status_snapshot": {"last_sync_at": "2026-04-20T12:00:00+00:00"},
            },
        )
        assert register_resp.status_code == 200, register_resp.text
        assert register_resp.json()["status"] == "registered"

        clients_resp = client.get(
            "/api/v1/clients",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert clients_resp.status_code == 200, clients_resp.text
        assert len(clients_resp.json()) == 1
        assert clients_resp.json()[0]["hostname"] == "host-local"

        summary_resp = client.get(
            "/api/v1/clients/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert summary_resp.status_code == 200, summary_resp.text
        assert summary_resp.json()["total_clients"] == 1
        assert summary_resp.json()["online_clients"] == 1
        assert summary_resp.json()["unique_empresas"] == 1

        config_command = client.post(
            "/api/v1/clients/client-local-001/config",
            headers={"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"},
            json={"payload": {"sync_interval_minutes": 10, "local_endpoint_url": "https://local.example/api/v2"}},
        )
        assert config_command.status_code == 200, config_command.text
        assert config_command.json()["status"] == "queued"

        pull_resp = client.get(
            "/api/v1/commands",
            headers={
                "X-Empresa-Id": "12345678000199",
                "X-Client-Id": "client-local-001",
                "X-Client-Token": "local-control-token-abcdefghijklmnopqrstuvwxyz12",
                "X-Correlation-Id": "corr-pull-001",
            },
        )
        assert pull_resp.status_code == 200, pull_resp.text
        assert len(pull_resp.json()) == 1
        command_id = pull_resp.json()[0]["id"]
        assert pull_resp.json()[0]["command_type"] == "update_config"

        result_resp = client.post(
            f"/api/v1/commands/{command_id}/result",
            headers={
                "X-Empresa-Id": "12345678000199",
                "X-Client-Id": "client-local-001",
                "X-Client-Token": "local-control-token-abcdefghijklmnopqrstuvwxyz12",
                "X-Correlation-Id": "corr-result-001",
            },
            json={
                "status": "completed",
                "result": {"updated": True},
                "config_snapshot": {"sync_interval_minutes": 10, "local_endpoint_url": "https://local.example/api/v2"},
                "status_snapshot": {"last_sync_at": "2026-04-20T12:15:00+00:00", "last_sync_status": "success"},
            },
        )
        assert result_resp.status_code == 200, result_resp.text
        assert result_resp.json()["status"] == "completed"

        client_state = client.get(
            "/api/v1/clients/client-local-001/config",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert client_state.status_code == 200, client_state.text
        assert client_state.json()["config_snapshot"]["sync_interval_minutes"] == 10
        assert client_state.json()["status_snapshot"]["last_sync_status"] == "success"

        sync_command = client.post(
            "/api/v1/clients/client-local-001/sync",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert sync_command.status_code == 200, sync_command.text
        assert sync_command.json()["status"] == "queued"

        logs_resp = client.get(
            "/api/v1/clients/client-local-001/logs",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert logs_resp.status_code == 200, logs_resp.text
        assert len(logs_resp.json()) >= 3
        assert any(log.get("correlation_id") == "corr-registration-001" for log in logs_resp.json())
        assert any(log.get("correlation_id") == "corr-result-001" for log in logs_resp.json())

    with SessionLocal() as session:
        commands = session.query(LocalClientCommand).all()
        logs = session.query(LocalClientLog).all()

    assert len(commands) == 2
    assert any(command.command_type == "force_sync" for command in commands)
    assert len(logs) >= 4
    assert any('"correlation_id": "corr-registration-001"' in log.detail_json for log in logs)

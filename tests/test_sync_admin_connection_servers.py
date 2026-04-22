from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin() -> None:
    db_path = Path("output/test_sync_admin_connection_servers.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = "output/test_sync_admin_connection_servers_token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_settings_manages_secure_connection_servers(monkeypatch) -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    def fake_get_server_settings(self):
        return {
            "ingestion_enabled": True,
            "max_batch_size": 1000,
            "retention_mode": "archive",
            "retention_months": 14,
            "connection_secrets_file": "output/tenant_connection_secrets.json",
        }

    def fake_fetch_source_configs(self):
        return [
            {
                "id": "src-1",
                "empresa_id": "12345678000199",
                "nome": "API segura",
                "connector_type": "api",
                "sync_interval_minutes": 15,
                "ativo": True,
                "last_run_at": None,
                "last_status": "pending",
                "last_error": None,
                "settings": {
                    "settings_file": "output/tenant_connection_secrets.json",
                    "settings_key": "server-ref-1",
                },
            }
        ]

    def fake_fetch_destination_configs(self):
        return []

    secure_calls: list[dict] = []
    rotate_calls: list[dict] = []
    update_calls: list[dict] = []

    def fake_create_secure_connection_config(self, **payload):
        secure_calls.append(payload)
        return {
            "scope": payload["scope"],
            "settings_key": "server-ref-1",
            "generated_access_key": "generated-server-key-123",
            "secrets_file": "output/tenant_connection_secrets.json",
            "config": {
                "id": "src-1",
                "connector_type": payload["connector_type"],
                "nome": payload["nome"],
                "settings": {
                    "settings_file": "output/tenant_connection_secrets.json",
                    "settings_key": "server-ref-1",
                },
            },
        }

    def fake_rotate_secure_connection_key(self, **payload):
        rotate_calls.append(payload)
        return {
            "settings_key": payload["settings_key"],
            "secrets_file": "output/tenant_connection_secrets.json",
            "access_key_field": payload.get("access_key_field") or "api_key",
            "generated_access_key": "rotated-server-key-456",
        }

    def fake_update_secure_connection_secret(self, **payload):
        update_calls.append(payload)
        return {
            "settings_key": payload["settings_key"],
            "secrets_file": "output/tenant_connection_secrets.json",
            "updated_fields": sorted(payload["secret_settings"].keys()),
        }

    monkeypatch.setattr(ControlService, "get_server_settings", fake_get_server_settings)
    monkeypatch.setattr(ControlService, "fetch_source_configs", fake_fetch_source_configs)
    monkeypatch.setattr(ControlService, "fetch_destination_configs", fake_fetch_destination_configs)
    monkeypatch.setattr(ControlService, "create_secure_connection_config", fake_create_secure_connection_config)
    monkeypatch.setattr(ControlService, "rotate_secure_connection_key", fake_rotate_secure_connection_key)
    monkeypatch.setattr(ControlService, "update_secure_connection_secret", fake_update_secure_connection_secret)

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        page = client.get("/settings")
        assert page.status_code == 200
        assert "Servidores de conexao seguros" in page.text
        assert "server-ref-1" in page.text
        assert "Rotacionar chave" in page.text
        assert "Atualizar segredo" in page.text

        create_resp = client.post(
            "/settings/secure-connection-config",
            data={
                "scope": "source",
                "nome": "API segura",
                "connector_type": "api",
                "sync_interval_minutes": "15",
                "settings_json": '{"endpoint": "/records"}',
                "secret_settings_json": '{"base_url": "https://api.exemplo.local"}',
                "generate_access_key": "true",
                "access_key_field": "api_key",
            },
            follow_redirects=False,
        )
        assert create_resp.status_code in (302, 303)
        assert "generated_key=generated-server-key-123" in create_resp.headers["location"]

        rotate_resp = client.post(
            "/settings/secure-connection-config/server-ref-1/rotate-key",
            data={"access_key_field": "api_key"},
            follow_redirects=False,
        )
        assert rotate_resp.status_code in (302, 303)
        assert "generated_key=rotated-server-key-456" in rotate_resp.headers["location"]

        update_resp = client.post(
            "/settings/secure-connection-config/server-ref-1/update-secret",
            data={
                "secret_settings_json": '{"base_url": "https://api-editada.exemplo.local", "region": "sa-east-1"}',
                "merge_mode": "true",
            },
            follow_redirects=False,
        )
        assert update_resp.status_code in (302, 303)
        assert "Segredo+do+servidor+atualizado" in update_resp.headers["location"]

    assert secure_calls[0]["scope"] == "source"
    assert secure_calls[0]["connector_type"] == "api"
    assert secure_calls[0]["secret_settings"]["base_url"] == "https://api.exemplo.local"
    assert secure_calls[0]["generate_access_key"] is True
    assert rotate_calls[0]["settings_key"] == "server-ref-1"
    assert rotate_calls[0]["access_key_field"] == "api_key"
    assert update_calls[0]["settings_key"] == "server-ref-1"
    assert update_calls[0]["secret_settings"]["base_url"] == "https://api-editada.exemplo.local"
    assert update_calls[0]["secret_settings"]["region"] == "sa-east-1"
    assert update_calls[0]["merge"] is True

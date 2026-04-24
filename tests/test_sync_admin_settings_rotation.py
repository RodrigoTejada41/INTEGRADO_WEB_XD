from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _prepare_sync_admin(db_name: str) -> None:
    db_path = Path(f"output/{db_name}")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/{db_name}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_settings_rotate_tenant_key_updates_agent_key_file_and_redirects_with_flash(monkeypatch) -> None:
    _prepare_sync_admin("test_settings_rotate_tenant_key.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    key_file = Path("output/test_settings_rotate_tenant_key.agent.key")
    if key_file.exists():
        key_file.unlink()

    def fake_rotate_tenant_key(self, empresa_id: str, actor: str | None = None):
        assert empresa_id == "12345678000199"
        assert actor == "admin"
        return {
            "empresa_id": empresa_id,
            "api_key": "rotated-key-123",
            "api_key_last_rotated_at": "2026-04-24T08:00:00+00:00",
            "api_key_expires_at": "2026-05-24T08:00:00+00:00",
            "status": "ok",
        }

    def fake_update_agent_key_file(self, api_key: str) -> str:
        key_file.write_text(api_key, encoding="utf-8")
        return str(key_file)

    monkeypatch.setattr(ControlService, "rotate_tenant_key", fake_rotate_tenant_key)
    monkeypatch.setattr(ControlService, "update_agent_key_file", fake_update_agent_key_file)

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        rotate_resp = client.post(
            "/settings/rotate-tenant-key",
            data={"empresa_id": "12345678000199"},
            follow_redirects=False,
        )
        assert rotate_resp.status_code in (302, 303)

    location = rotate_resp.headers["location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    assert parsed.path == "/settings"
    assert "Chave rotacionada e aplicada no agente" in params["flash"][0]
    assert str(key_file) in params["flash"][0]
    assert params["generated_key"][0] == "rotated-key-123"
    assert params["generated_key_expires_at"][0] == "2026-05-24T08:00:00+00:00"
    assert key_file.read_text(encoding="utf-8") == "rotated-key-123"

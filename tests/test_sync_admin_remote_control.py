from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _prepare_sync_admin(db_name: str, allowed_ips: str = "") -> None:
    db_path = Path(f"output/{db_name}")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["REMOTE_CONTROL_ALLOWED_IPS"] = allowed_ips
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/{db_name}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))

    for module_name in list(sys.modules):
        if module_name == "app.main" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


def test_remote_control_endpoints_require_token_and_update_state() -> None:
    _prepare_sync_admin("test_sync_admin_remote_control.db")

    from app.main import app

    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/config")
        assert unauthorized.status_code == 401

        headers = {"X-Local-Token": "local-token-test"}

        config_resp = client.get("/api/v1/config", headers=headers)
        assert config_resp.status_code == 200, config_resp.text
        assert config_resp.json()["empresa_id"] == "12345678000199"
        assert "X-Request-Id" in config_resp.headers
        assert config_resp.headers["X-Correlation-Id"] == config_resp.headers["X-Request-Id"]
        assert "X-Response-Time-ms" in config_resp.headers

        correlated_resp = client.get(
            "/api/v1/status",
            headers={**headers, "X-Correlation-Id": "sync-admin-corr-001"},
        )
        assert correlated_resp.status_code == 200, correlated_resp.text
        assert correlated_resp.headers["X-Correlation-Id"] == "sync-admin-corr-001"

        update_resp = client.post(
            "/api/v1/config",
            headers=headers,
            json={
                "sync_interval_minutes": 10,
                "command_poll_interval_seconds": 45,
                "remote_control_allowed_ips": ["testclient"],
            },
        )
        assert update_resp.status_code == 200, update_resp.text
        assert update_resp.json()["sync_interval_minutes"] == 10
        assert update_resp.json()["command_poll_interval_seconds"] == 45

        force_resp = client.post("/api/v1/sync/force", headers=headers)
        assert force_resp.status_code == 200, force_resp.text
        assert force_resp.json()["status"] == "success"

        status_resp = client.get("/api/v1/status", headers=headers)
        assert status_resp.status_code == 200, status_resp.text
        assert status_resp.json()["last_sync_status"] == "success"
        assert status_resp.json()["installation_id"]
        assert status_resp.json()["uptime_seconds"] >= 0


def test_remote_control_token_allowlist_blocks_unlisted_ip() -> None:
    _prepare_sync_admin("test_sync_admin_remote_control_blocked.db", allowed_ips="127.0.0.1")

    from app.main import app

    with TestClient(app) as client:
        blocked = client.get("/api/v1/config", headers={"X-Local-Token": "local-token-test"})
        assert blocked.status_code == 403
        assert blocked.json()["detail"] == "Source IP not allowed."


def test_remote_control_token_allowlist_accepts_listed_ip() -> None:
    _prepare_sync_admin("test_sync_admin_remote_control_allowed.db", allowed_ips="testclient")

    from app.main import app

    with TestClient(app) as client:
        allowed = client.get("/api/v1/config", headers={"X-Local-Token": "local-token-test"})
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["empresa_id"] == "12345678000199"

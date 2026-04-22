from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def test_sync_admin_health_and_readiness() -> None:
    db_path = Path("output/test_sync_admin_health.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["CONTROL_API_BASE_URL"] = "http://127.0.0.1:59999"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = "output/test_sync_admin_health_token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))

    for module_name in list(sys.modules):
        if module_name == "app.main" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)

    from app.main import app

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "online"

        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["status"] == "live"

        ready = client.get("/health/ready")
        assert ready.status_code == 503
        payload = ready.json()["detail"]
        assert payload["status"] == "not_ready"
        assert payload["components"]["database"] == "ready"
        assert "error" in payload["components"]["control_api"]

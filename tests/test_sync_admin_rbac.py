from __future__ import annotations

import os
import sys
from pathlib import Path


def test_sync_admin_role_based_access() -> None:
    db_path = Path(f"output/test_sync_admin_rbac_{os.getpid()}.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/test_sync_admin_rbac_{os.getpid()}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        settings_resp = client.get("/settings")
        assert settings_resp.status_code == 200

        create_analyst = client.post(
            "/settings/users",
            data={
                "username": "analyst1",
                "full_name": "Analyst User",
                "password": "analyst123",
                "role": "analyst",
            },
            follow_redirects=False,
        )
        assert create_analyst.status_code in (302, 303)

        create_viewer = client.post(
            "/settings/users",
            data={
                "username": "viewer1",
                "full_name": "Viewer User",
                "password": "viewer123",
                "role": "viewer",
            },
            follow_redirects=False,
        )
        assert create_viewer.status_code in (302, 303)

        client.post("/logout", follow_redirects=False)

        analyst_login = client.post(
            "/login",
            data={"username": "analyst1", "password": "analyst123"},
            follow_redirects=False,
        )
        assert analyst_login.status_code in (302, 303)

        analyst_records = client.get("/records")
        assert analyst_records.status_code == 200

        analyst_history = client.get("/history")
        assert analyst_history.status_code == 200

        analyst_settings = client.get("/settings")
        assert analyst_settings.status_code == 403

        client.post("/logout", follow_redirects=False)

        viewer_login = client.post(
            "/login",
            data={"username": "viewer1", "password": "viewer123"},
            follow_redirects=False,
        )
        assert viewer_login.status_code in (302, 303)

        viewer_dashboard = client.get("/dashboard")
        assert viewer_dashboard.status_code == 200

        viewer_records = client.get("/records")
        assert viewer_records.status_code == 403

        viewer_settings = client.get("/settings")
        assert viewer_settings.status_code == 403

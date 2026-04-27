from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_sync_admin_path() -> None:
    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_role_based_access() -> None:
    db_path = Path("output/test_sync_admin_rbac.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"

    _ensure_sync_admin_path()

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

        client.post("/logout", follow_redirects=False)

        viewer_login = client.post(
            "/login",
            data={"username": "viewer1", "password": "viewer123"},
            follow_redirects=False,
        )
        assert viewer_login.status_code in (302, 303)

        viewer_dashboard = client.get("/dashboard")
        assert viewer_dashboard.status_code == 200


def test_admin_can_preview_any_client_portal_scope(monkeypatch) -> None:
    _ensure_sync_admin_path()

    from app.models.user import User
    from app.web.deps import require_client_portal_access
    from app.web.routes import pages

    captured: dict[str, str | None] = {}

    def fake_fetch_report_branch_options(self, **kwargs):
        captured.update(kwargs)
        return ["0001", "0002"]

    monkeypatch.setattr(
        pages.ControlService,
        "fetch_report_branch_options",
        fake_fetch_report_branch_options,
    )

    admin_user = User(
        id=1,
        username="admin",
        full_name="Admin",
        password_hash="hash",
        role="admin",
    )

    assert require_client_portal_access(admin_user) is admin_user

    scope = pages._resolve_client_portal_scope(
        current_user=admin_user,
        db=object(),
        requested_empresa_id="99887766000155",
        requested_branch_code="0002",
        start_date="2026-04-01",
        end_date="2026-04-27",
        terminal_code="PDV-01",
    )

    assert captured["empresa_id"] == "99887766000155"
    assert scope.empresa_id == "99887766000155"
    assert scope.allowed_branch_codes == ["0001", "0002"]
    assert scope.selected_branch_code == "0002"

from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin() -> None:
    db_path = Path("output/test_sync_admin_exports.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = "output/test_sync_admin_exports_token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_export_formats_and_snapshot() -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        csv_resp = client.get("/records/export.csv")
        assert csv_resp.status_code == 200
        assert csv_resp.headers["content-type"].startswith("text/csv")

        xlsx_resp = client.get("/records/export.xlsx")
        assert xlsx_resp.status_code == 200
        assert xlsx_resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert xlsx_resp.content[:2] == b"PK"

        pdf_resp = client.get("/records/export.pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"].startswith("application/pdf")
        assert pdf_resp.content.startswith(b"%PDF")

        md_resp = client.get("/dashboard/export.md")
        assert md_resp.status_code == 200
        assert md_resp.headers["content-type"].startswith("text/markdown")
        assert "Snapshot local do sync-admin" in md_resp.text

    snapshot_path = Path(".cerebro-vivo/Conhecimento/hubs/sync-admin/snapshot.md")
    assert snapshot_path.exists()

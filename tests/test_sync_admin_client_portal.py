from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"{db_path.as_posix()}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_client_user_sees_only_own_portal(monkeypatch, tmp_path: Path) -> None:
    _prepare_sync_admin(tmp_path / "test_sync_admin_client_portal.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_report_overview",
        lambda self, **kwargs: {
            "empresa_id": kwargs.get("empresa_id") or "12345678000199",
            "total_records": 8,
            "distinct_products": 3,
            "distinct_branches": 1,
            "distinct_terminals": 2,
            "total_sales_value": "800.00",
            "first_sale_date": "2026-04-01",
            "last_sale_date": "2026-04-20",
        },
    )
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(
        ControlService,
        "fetch_report_branch_options",
        lambda self, **kwargs: ["0001", "0002", "0003"],
    )

    with TestClient(app) as client:
        admin_login = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert admin_login.status_code in (302, 303)

        create_client = client.post(
            "/settings/users",
            data={
                "username": "cliente01",
                "full_name": "Cliente 01",
                "password": "cliente123",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "company",
            },
            follow_redirects=False,
        )
        assert create_client.status_code in (302, 303)

        client.post("/logout", follow_redirects=False)

        client_login = client.post(
            "/login",
            data={"username": "cliente01", "password": "cliente123"},
            follow_redirects=False,
        )
        assert client_login.status_code in (302, 303)
        assert client_login.headers["location"] == "/client/dashboard"

        client_dashboard = client.get("/client/dashboard")
        assert client_dashboard.status_code == 200
        assert "Portal do Cliente" in client_dashboard.text
        assert "55555555000155" in client_dashboard.text
        assert "0001" in client_dashboard.text
        assert "0003" in client_dashboard.text

        client_reports = client.get("/client/reports")
        assert client_reports.status_code == 200
        assert "Relatorios do Cliente" in client_reports.text
        assert "800.00" in client_reports.text
        assert "Todas as filiais permitidas" in client_reports.text

        blocked_settings = client.get("/settings")
        assert blocked_settings.status_code == 403

        blocked_admin_reports = client.get("/reports")
        assert blocked_admin_reports.status_code == 403


def test_sync_admin_client_reports_compare_and_export_use_logged_empresa(monkeypatch, tmp_path: Path) -> None:
    _prepare_sync_admin(tmp_path / "test_sync_admin_client_reports_export.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    overview_calls: list[dict] = []
    recent_calls: list[dict] = []

    def fake_overview(self, **kwargs):
        overview_calls.append(dict(kwargs))
        if kwargs.get("start_date") == "2026-04-01":
            return {
                "empresa_id": kwargs.get("empresa_id") or "55555555000155",
                "total_records": 8,
                "distinct_products": 3,
                "distinct_branches": 1,
                "distinct_terminals": 2,
                "total_sales_value": "800.00",
                "first_sale_date": "2026-04-01",
                "last_sale_date": "2026-04-20",
            }
        return {
            "empresa_id": kwargs.get("empresa_id") or "55555555000155",
            "total_records": 5,
            "distinct_products": 2,
            "distinct_branches": 1,
            "distinct_terminals": 1,
            "total_sales_value": "500.00",
            "first_sale_date": "2026-03-12",
            "last_sale_date": "2026-03-31",
        }

    def fake_recent(self, **kwargs):
        recent_calls.append(dict(kwargs))
        return {
            "items": [
                {
                    "uuid": "sale-client-1",
                    "produto": "Produto Cliente",
                    "valor": "90.00",
                    "data": "2026-04-20",
                    "data_atualizacao": "2026-04-20T10:00:00Z",
                    "branch_code": "BR-01",
                    "terminal_code": "PDV-01",
                }
            ]
        }

    monkeypatch.setattr(ControlService, "fetch_report_overview", fake_overview)
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", fake_recent)
    monkeypatch.setattr(
        ControlService,
        "fetch_report_branch_options",
        lambda self, **kwargs: ["0001", "0003"],
    )

    with TestClient(app) as client:
        admin_login = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert admin_login.status_code in (302, 303)

        create_client = client.post(
            "/settings/users",
            data={
                "username": "cliente_export",
                "full_name": "Cliente Export",
                "password": "cliente123",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "branch_set",
                "allowed_branch_codes": ["0001", "0003"],
            },
            follow_redirects=False,
        )
        assert create_client.status_code in (302, 303)

        client.post("/logout", follow_redirects=False)

        client_login = client.post(
            "/login",
            data={"username": "cliente_export", "password": "cliente123"},
            follow_redirects=False,
        )
        assert client_login.status_code in (302, 303)
        assert client_login.headers["location"] == "/client/dashboard"

        reports_page = client.get(
            "/client/reports",
            params={"start_date": "2026-04-01", "end_date": "2026-04-20", "empresa_id": "99999999000199"},
        )
        assert reports_page.status_code == 200
        assert "Comparativo com periodo anterior" in reports_page.text
        assert "sale-client-1" in reports_page.text

        csv_resp = client.get("/client/reports/export.csv", params={"empresa_id": "99999999000199"})
        assert csv_resp.status_code == 200
        assert "sale-client-1" in csv_resp.text

    assert overview_calls
    assert recent_calls
    assert all(call.get("empresa_id") == "55555555000155" for call in overview_calls)
    assert all(call.get("empresa_id") == "55555555000155" for call in recent_calls)


def test_sync_admin_client_branch_scope_blocks_unauthorized_branch(monkeypatch, tmp_path: Path) -> None:
    _prepare_sync_admin(tmp_path / "test_sync_admin_client_branch_scope.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_report_overview",
        lambda self, **kwargs: {
            "empresa_id": kwargs.get("empresa_id") or "55555555000155",
            "total_records": 2,
            "distinct_products": 1,
            "distinct_branches": 2,
            "distinct_terminals": 1,
            "total_sales_value": "100.00",
            "first_sale_date": "2026-04-01",
            "last_sale_date": "2026-04-20",
        },
    )
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(
        ControlService,
        "fetch_report_branch_options",
        lambda self, **kwargs: ["0001", "0002", "0003"],
    )

    with TestClient(app) as client:
        admin_login = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert admin_login.status_code in (302, 303)

        create_client = client.post(
            "/settings/users",
            data={
                "username": "cliente_filial_limitado",
                "full_name": "Cliente Filial Limitado",
                "password": "cliente123",
                "role": "client",
                "empresa_id": "55555555000155",
                "scope_type": "branch_set",
                "allowed_branch_codes": ["0001", "0003"],
            },
            follow_redirects=False,
        )
        assert create_client.status_code in (302, 303)

        client.post("/logout", follow_redirects=False)

        client_login = client.post(
            "/login",
            data={"username": "cliente_filial_limitado", "password": "cliente123"},
            follow_redirects=False,
        )
        assert client_login.status_code in (302, 303)

        allowed = client.get("/client/reports", params={"branch_code": "0003"})
        assert allowed.status_code == 200

        blocked = client.get("/client/reports", params={"branch_code": "0002"})
        assert blocked.status_code == 403

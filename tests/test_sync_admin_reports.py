from __future__ import annotations

import os
import sys
from pathlib import Path


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


def _overview_payload(**overrides):
    payload = {
        "empresa_id": "12345678000199",
        "total_records": 12,
        "distinct_products": 4,
        "distinct_branches": 2,
        "distinct_terminals": 3,
        "total_sales_value": "1250.50",
        "first_sale_date": "2026-04-01",
        "last_sale_date": "2026-04-20",
        "start_date": "2026-04-01",
        "end_date": "2026-04-20",
        "branch_code": None,
        "terminal_code": None,
    }
    payload.update(overrides)
    return payload


def test_sync_admin_reports_page_renders_backend_report_data(monkeypatch) -> None:
    _prepare_sync_admin("test_sync_admin_reports_page.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_report_overview",
        lambda self, **kwargs: {
            "empresa_id": "12345678000199",
            "total_records": 12,
            "distinct_products": 4,
            "distinct_branches": 2,
            "distinct_terminals": 3,
            "total_sales_value": "1250.50",
            "first_sale_date": "2026-04-01",
            "last_sale_date": "2026-04-20",
            "start_date": "2026-04-01",
            "end_date": "2026-04-20",
            "branch_code": kwargs.get("branch_code"),
            "terminal_code": kwargs.get("terminal_code"),
        },
    )
    monkeypatch.setattr(
        ControlService,
        "fetch_report_daily_sales",
        lambda self, **kwargs: {
            "items": [
                {"day": "2026-04-19", "total_records": 5, "total_sales_value": "500.00"},
                {"day": "2026-04-20", "total_records": 7, "total_sales_value": "750.50"},
            ]
        },
    )
    monkeypatch.setattr(
        ControlService,
        "fetch_report_top_products",
        lambda self, **kwargs: {
            "items": [
                {"produto": "Produto A", "total_records": 6, "total_sales_value": "600.00"},
                {"produto": "Produto B", "total_records": 3, "total_sales_value": "300.00"},
            ]
        },
    )
    monkeypatch.setattr(
        ControlService,
        "fetch_report_recent_sales",
        lambda self, **kwargs: {
            "items": [
                {
                    "uuid": "sale-1",
                    "produto": "Produto A",
                    "valor": "150.00",
                    "data": "2026-04-20",
                    "data_atualizacao": "2026-04-20T10:00:00Z",
                    "branch_code": "BR-01",
                    "terminal_code": "PDV-01",
                }
            ]
        },
    )

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        reports_page = client.get(
            "/reports",
            params={
                "start_date": "2026-04-01",
                "end_date": "2026-04-20",
                "branch_code": "BR-01",
                "terminal_code": "PDV-01",
            },
        )
        assert reports_page.status_code == 200
        assert "Relatorios" in reports_page.text
        assert "1250.50" in reports_page.text
        assert "Produto A" in reports_page.text
        assert "sale-1" in reports_page.text
        assert "Ticket medio" in reports_page.text
        assert "Produto lider" in reports_page.text


def test_sync_admin_reports_permissions(monkeypatch) -> None:
    _prepare_sync_admin("test_sync_admin_reports_permissions.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(
        ControlService,
        "fetch_report_overview",
        lambda self, **kwargs: {
            "empresa_id": "12345678000199",
            "total_records": 0,
            "distinct_products": 0,
            "distinct_branches": 0,
            "distinct_terminals": 0,
            "total_sales_value": "0.00",
            "first_sale_date": None,
            "last_sale_date": None,
        },
    )
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", lambda self, **kwargs: {"items": []})

    with TestClient(app) as client:
        admin_login = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert admin_login.status_code in (302, 303)

        create_analyst = client.post(
            "/settings/users",
            data={
                "username": "analyst_reports",
                "full_name": "Analyst Reports",
                "password": "analyst123",
                "role": "analyst",
            },
            follow_redirects=False,
        )
        assert create_analyst.status_code in (302, 303)

        create_viewer = client.post(
            "/settings/users",
            data={
                "username": "viewer_reports",
                "full_name": "Viewer Reports",
                "password": "viewer123",
                "role": "viewer",
            },
            follow_redirects=False,
        )
        assert create_viewer.status_code in (302, 303)

        client.post("/logout", follow_redirects=False)

        analyst_login = client.post(
            "/login",
            data={"username": "analyst_reports", "password": "analyst123"},
            follow_redirects=False,
        )
        assert analyst_login.status_code in (302, 303)
        analyst_reports = client.get("/reports")
        assert analyst_reports.status_code == 200

        client.post("/logout", follow_redirects=False)

        viewer_login = client.post(
            "/login",
            data={"username": "viewer_reports", "password": "viewer123"},
            follow_redirects=False,
        )
        assert viewer_login.status_code in (302, 303)
        viewer_reports = client.get("/reports")
        assert viewer_reports.status_code == 403


def test_sync_admin_reports_page_shows_period_comparison(monkeypatch) -> None:
    _prepare_sync_admin("test_sync_admin_reports_compare.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    def fake_overview(self, **kwargs):
        if kwargs.get("start_date") == "2026-04-01":
            return _overview_payload(
                total_records=12,
                total_sales_value="1250.50",
                start_date="2026-04-01",
                end_date="2026-04-20",
            )
        return _overview_payload(
            total_records=8,
            total_sales_value="950.00",
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

    monkeypatch.setattr(ControlService, "fetch_report_overview", fake_overview)
    monkeypatch.setattr(ControlService, "fetch_report_daily_sales", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_top_products", lambda self, **kwargs: {"items": []})
    monkeypatch.setattr(ControlService, "fetch_report_recent_sales", lambda self, **kwargs: {"items": []})

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        reports_page = client.get(
            "/reports",
            params={"start_date": "2026-04-01", "end_date": "2026-04-20"},
        )
        assert reports_page.status_code == 200
        assert "Comparativo com periodo anterior" in reports_page.text
        assert "950.00" in reports_page.text
        assert "+300.50" in reports_page.text
        assert "(+31.6%)" in reports_page.text


def test_sync_admin_reports_export_routes(monkeypatch) -> None:
    _prepare_sync_admin("test_sync_admin_reports_exports.db")

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import ControlService

    monkeypatch.setattr(ControlService, "fetch_report_overview", lambda self, **kwargs: _overview_payload())
    monkeypatch.setattr(
        ControlService,
        "fetch_report_daily_sales",
        lambda self, **kwargs: {
            "items": [
                {"day": "2026-04-19", "total_records": 5, "total_sales_value": "500.00"},
            ]
        },
    )
    monkeypatch.setattr(
        ControlService,
        "fetch_report_top_products",
        lambda self, **kwargs: {
            "items": [
                {"produto": "Produto A", "total_records": 6, "total_sales_value": "600.00"},
            ]
        },
    )
    monkeypatch.setattr(
        ControlService,
        "fetch_report_recent_sales",
        lambda self, **kwargs: {
            "items": [
                {
                    "uuid": "sale-1",
                    "produto": "Produto A",
                    "valor": "150.00",
                    "data": "2026-04-20",
                    "data_atualizacao": "2026-04-20T10:00:00Z",
                    "branch_code": "BR-01",
                    "terminal_code": "PDV-01",
                }
            ]
        },
    )

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        csv_resp = client.get("/reports/export.csv")
        assert csv_resp.status_code == 200
        assert csv_resp.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=reports.csv" == csv_resp.headers["content-disposition"]
        assert "sale-1" in csv_resp.text

        xlsx_resp = client.get("/reports/export.xlsx")
        assert xlsx_resp.status_code == 200
        assert (
            xlsx_resp.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert "attachment; filename=reports.xlsx" == xlsx_resp.headers["content-disposition"]
        assert xlsx_resp.content.startswith(b"PK")

        pdf_resp = client.get("/reports/export.pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert "attachment; filename=reports.pdf" == pdf_resp.headers["content-disposition"]
        assert pdf_resp.content.startswith(b"%PDF")

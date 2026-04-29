from __future__ import annotations

import os
import sys
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

        client.post("/logout", follow_redirects=False)

        client_login = client.post(
            "/client/login",
            data={"username": "adm", "password": "25032015Lu@@"},
            follow_redirects=False,
        )
        assert client_login.status_code in (302, 303)
        assert client_login.headers["location"] == "/client/reports"

        client_admin_dashboard = client.get("/dashboard")
        assert client_admin_dashboard.status_code == 403


def test_admin_can_preview_any_client_portal_scope(monkeypatch) -> None:
    _ensure_sync_admin_path()

    from app.models.user import User
    from app.web.deps import ROLE_PERMISSIONS, require_client_portal_access
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
    assert "client.dashboard.view" in ROLE_PERMISSIONS["admin"]
    assert "client.reports.view" in ROLE_PERMISSIONS["admin"]


def test_report_period_is_limited_to_fourteen_months() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    start_date, end_date, preset = pages._resolve_report_period(
        "custom",
        "2024-01-01",
        "2026-04-28",
    )

    assert preset == "custom"
    assert end_date == "2026-04-28"
    assert start_date == "2025-02-25"


def test_report_pdf_is_structured_and_readable() -> None:
    _ensure_sync_admin_path()

    from app.services.export_service import report_to_pdf_bytes

    pdf = report_to_pdf_bytes(
        {
            "empresa_id": "12345678000199",
            "start_date": "2025-02-25",
            "end_date": "2026-04-28",
            "total_records": 1,
            "total_sales_value": "99.90",
            "distinct_products": 1,
            "distinct_branches": 0,
            "distinct_terminals": 0,
            "first_sale_date": "2026-04-22",
            "last_sale_date": "2026-04-22",
        },
        [{"day": "2026-04-22", "total_records": 1, "total_sales_value": "99.90"}],
        [{"produto": "Teste Integracao Real Atualizado", "total_records": 1, "total_sales_value": "99.90"}],
        [
            {
                "uuid": "codex-1776827155-13749",
                "produto": "Teste Integracao Real Atualizado",
                "valor": "99.90",
                "data": "2026-04-22",
            }
        ],
        title="Relatorios do cliente",
    )

    assert pdf.startswith(b"%PDF-1.4")
    assert b"Filtros e resumo" in pdf
    assert b"Indicadores" in pdf
    assert b"Serie diaria" in pdf
    assert b"Top produtos" in pdf
    assert b"Vendas recentes" in pdf
    assert b"BT /F1 18 Tf" in pdf


def test_report_csv_and_excel_are_client_readable() -> None:
    _ensure_sync_admin_path()

    from app.services.export_service import report_recent_sales_to_csv, report_to_xlsx_bytes

    sale = {
        "uuid": "codex-1776827155-13749",
        "produto": "Teste Integracao Real Atualizado",
        "valor": "99.90",
        "data": "2026-04-22",
        "data_atualizacao": "2026-04-22T10:00:00",
        "branch_code": "0001",
        "terminal_code": "PDV-01",
        "forma_pagamento": "PIX",
        "tipo_venda": "Balcao",
        "familia_produto": "Teste",
        "campo_extra_que_nao_pode_quebrar_csv": "x",
    }

    csv_text = report_recent_sales_to_csv([sale])

    assert csv_text.splitlines()[0] == "Data;Produto;Valor;Pagamento;Tipo;Familia;Filial;Terminal;Codigo"
    assert "Teste Integracao Real Atualizado" in csv_text
    assert "campo_extra" not in csv_text

    xlsx_bytes = report_to_xlsx_bytes(
        {
            "empresa_id": "12345678000199",
            "start_date": "2025-02-25",
            "end_date": "2026-04-28",
            "total_records": 1,
            "total_sales_value": "99.90",
            "distinct_products": 1,
        },
        [{"day": "2026-04-22", "total_records": 1, "total_sales_value": "99.90"}],
        [{"produto": "Teste Integracao Real Atualizado", "total_records": 1, "total_sales_value": "99.90"}],
        [sale],
    )

    with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as archive:
        workbook = archive.read("xl/workbook.xml").decode("utf-8")
        first_sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        sales_sheet = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")

    assert "Resumo" in workbook
    assert "Vendas" in workbook
    assert "Produtos" in workbook
    assert "Dias" in workbook
    assert "Total faturado" in first_sheet
    assert "Pagamento" in sales_sheet
    assert "Familia" in sales_sheet


def test_report_dashboard_uses_modern_bi_layout() -> None:
    template = (
        ROOT
        / "sync-admin"
        / "app"
        / "templates"
        / "partials"
        / "report_dashboard_content.html"
    ).read_text(encoding="utf-8")
    script = (ROOT / "sync-admin" / "app" / "static" / "js" / "reports.js").read_text(
        encoding="utf-8"
    )

    assert "Dashboard de Performance" in template
    assert "bi-workspace-grid" in template
    assert "bi-filter-rail" in template
    assert "Evolucao de vendas no tempo" in template
    assert "Distribuicao por categoria" in template
    assert "Ranking executivo" in template
    assert "data-table-pagination" in template
    assert "replaceDashboardFrom" in script
    assert "event.preventDefault()" in script


def test_sync_admin_uses_adminlte_shell_globally() -> None:
    base = (ROOT / "sync-admin" / "app" / "templates" / "base.html").read_text(
        encoding="utf-8"
    )
    login = (ROOT / "sync-admin" / "app" / "templates" / "login.html").read_text(
        encoding="utf-8"
    )
    client_login = (
        ROOT / "sync-admin" / "app" / "templates" / "client_login.html"
    ).read_text(encoding="utf-8")
    components = (
        ROOT
        / "sync-admin"
        / "app"
        / "templates"
        / "partials"
        / "adminlte_components.html"
    ).read_text(encoding="utf-8")

    assert "adminlte.min.css" in base
    assert "main-sidebar" in base
    assert "main-header navbar" in base
    assert "content-wrapper" in base
    assert "content-header" in base
    assert "main-footer" in base
    assert "nav-sidebar" in base
    assert "login-page" in login
    assert "card-outline card-primary" in login
    assert "Portal do Cliente" in client_login
    assert "card-outline card-success" in client_login
    assert "macro small_box" in components
    assert "macro badge_status" in components

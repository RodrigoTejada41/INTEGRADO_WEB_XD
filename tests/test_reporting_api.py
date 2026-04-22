from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _reset_backend_modules() -> None:
    prefixes = (
        "backend.api",
        "backend.config",
        "backend.main",
        "backend.services",
    )
    for module_name in list(sys.modules):
        if module_name == "backend.main" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


def test_reporting_endpoints_are_multi_tenant_ready_for_frontend() -> None:
    db_path = Path("output/test_reporting_api.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app

    with TestClient(app) as client:
        audit_headers = {"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"}
        tenant_a = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "12345678000199", "nome": "Empresa A"},
        )
        tenant_b = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "98765432000155", "nome": "Empresa B"},
        )
        assert tenant_a.status_code == 200, tenant_a.text
        assert tenant_b.status_code == 200, tenant_b.text
        api_key_a = tenant_a.json()["api_key"]
        api_key_b = tenant_b.json()["api_key"]

        payload_a = {
            "empresa_id": "12345678000199",
            "records": [
                {
                    "uuid": "aaaaaaaa-1111-1111-1111-111111111111",
                    "branch_code": "BR-01",
                    "terminal_code": "PDV-01",
                    "produto": "Produto A",
                    "valor": "100.00",
                    "data": "2026-04-10",
                    "data_atualizacao": "2026-04-10T10:00:00Z",
                },
                {
                    "uuid": "aaaaaaaa-2222-1111-1111-111111111111",
                    "branch_code": "BR-01",
                    "terminal_code": "PDV-02",
                    "produto": "Produto A",
                    "valor": "150.00",
                    "data": "2026-04-11",
                    "data_atualizacao": "2026-04-11T10:00:00Z",
                },
                {
                    "uuid": "aaaaaaaa-3333-1111-1111-111111111111",
                    "branch_code": "BR-02",
                    "terminal_code": "PDV-03",
                    "produto": "Produto B",
                    "valor": "90.00",
                    "data": "2026-04-11",
                    "data_atualizacao": "2026-04-11T11:00:00Z",
                },
            ],
        }
        payload_b = {
            "empresa_id": "98765432000155",
            "records": [
                {
                    "uuid": "bbbbbbbb-1111-1111-1111-111111111111",
                    "branch_code": "BR-X",
                    "terminal_code": "PDV-X",
                    "produto": "Produto Externo",
                    "valor": "999.00",
                    "data": "2026-04-11",
                    "data_atualizacao": "2026-04-11T10:00:00Z",
                }
            ],
        }
        sync_a = client.post(
            "/sync",
            headers={"X-Empresa-Id": "12345678000199", "X-API-Key": api_key_a},
            json=payload_a,
        )
        sync_b = client.post(
            "/sync",
            headers={"X-Empresa-Id": "98765432000155", "X-API-Key": api_key_b},
            json=payload_b,
        )
        assert sync_a.status_code == 200, sync_a.text
        assert sync_b.status_code == 200, sync_b.text

        overview = client.get(
            "/admin/tenants/12345678000199/reports/overview",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"start_date": "2026-04-10", "end_date": "2026-04-11"},
        )
        assert overview.status_code == 200, overview.text
        assert overview.json()["empresa_id"] == "12345678000199"
        assert overview.json()["total_records"] == 3
        assert overview.json()["distinct_products"] == 2
        assert float(overview.json()["total_sales_value"]) == 340.0

        daily = client.get(
            "/admin/tenants/12345678000199/reports/daily-sales",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"start_date": "2026-04-10", "end_date": "2026-04-11"},
        )
        assert daily.status_code == 200, daily.text
        assert [item["day"] for item in daily.json()["items"]] == ["2026-04-10", "2026-04-11"]
        assert float(daily.json()["items"][1]["total_sales_value"]) == 240.0

        top_products = client.get(
            "/admin/tenants/12345678000199/reports/top-products",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"limit": 5, "branch_code": "BR-01"},
        )
        assert top_products.status_code == 200, top_products.text
        assert top_products.json()["items"][0]["produto"] == "Produto A"
        assert len(top_products.json()["items"]) == 1
        assert float(top_products.json()["items"][0]["total_sales_value"]) == 250.0

        recent_sales = client.get(
            "/admin/tenants/12345678000199/reports/recent-sales",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"limit": 2},
        )
        assert recent_sales.status_code == 200, recent_sales.text
        assert len(recent_sales.json()["items"]) == 2
        assert recent_sales.json()["items"][0]["uuid"] == "aaaaaaaa-3333-1111-1111-111111111111"
        assert all(item["produto"] != "Produto Externo" for item in recent_sales.json()["items"])

        invalid_range = client.get(
            "/admin/tenants/12345678000199/reports/overview",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"start_date": "2026-04-12", "end_date": "2026-04-11"},
        )
        assert invalid_range.status_code == 400
        assert invalid_range.json()["detail"] == "end_date deve ser maior ou igual a start_date."

from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


def _reset_backend_modules() -> None:
    prefixes = ("backend.api", "backend.config", "backend.main", "backend.services", "backend.repositories")
    for module_name in list(sys.modules):
        if module_name == "backend.main" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


def _prepare_backend(db_name: str) -> None:
    db_path = Path(f"output/{db_name}")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    _reset_backend_modules()
    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()


def test_backend_api_e2e_contract_covers_registration_sync_and_key_rotation() -> None:
    _prepare_backend("test_api_e2e_contract.db")

    from backend.main import app

    admin_headers = {"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"}
    empresa_id = "12345678000199"

    with TestClient(app) as client:
        provision_resp = client.post(
            "/admin/tenants",
            headers=admin_headers,
            json={"empresa_id": empresa_id, "nome": "Empresa E2E"},
        )
        assert provision_resp.status_code == 200, provision_resp.text
        initial_api_key = provision_resp.json()["api_key"]

        register_resp = client.post(
            "/api/v1/register",
            headers={
                "X-Empresa-Id": empresa_id,
                "X-API-Key": initial_api_key,
                "X-Correlation-Id": "corr-register-e2e",
            },
            json={
                "client_id": "client-e2e-001",
                "hostname": "host-e2e",
                "ip": "10.0.0.42",
                "endpoint_url": "https://client-e2e.local/api",
                "token": "local-control-token-e2e-abcdefghijklmnopqrstuvwxyz",
                "token_expires_at": (datetime.now(UTC) + timedelta(days=7)).isoformat(),
                "config_snapshot": {"sync_interval_minutes": 16},
                "status_snapshot": {"last_sync_at": "2026-04-24T08:00:00+00:00"},
            },
        )
        assert register_resp.status_code == 200, register_resp.text
        assert register_resp.json()["status"] == "registered"

        sync_insert_resp = client.post(
            "/sync",
            headers={"X-Empresa-Id": empresa_id, "X-API-Key": initial_api_key},
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "11111111-1111-1111-1111-111111111111",
                        "produto": "Produto E2E",
                        "valor": "100.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:00:00Z",
                    }
                ],
            },
        )
        assert sync_insert_resp.status_code == 200, sync_insert_resp.text
        assert sync_insert_resp.json()["inserted_count"] == 1
        assert sync_insert_resp.json()["updated_count"] == 0

        mismatch_resp = client.post(
            "/sync",
            headers={"X-Empresa-Id": empresa_id, "X-API-Key": initial_api_key},
            json={
                "empresa_id": "98765432000155",
                "records": [
                    {
                        "uuid": "22222222-2222-2222-2222-222222222222",
                        "produto": "Produto Invalido",
                        "valor": "50.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:05:00Z",
                    }
                ],
            },
        )
        assert mismatch_resp.status_code == 403, mismatch_resp.text
        assert mismatch_resp.json()["detail"] == "empresa_id do payload difere da credencial."

        rotate_resp = client.post(
            f"/admin/tenants/{empresa_id}/rotate-key",
            headers=admin_headers,
        )
        assert rotate_resp.status_code == 200, rotate_resp.text
        rotated_api_key = rotate_resp.json()["api_key"]
        assert rotated_api_key != initial_api_key

        old_key_resp = client.post(
            "/sync",
            headers={"X-Empresa-Id": empresa_id, "X-API-Key": initial_api_key},
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "11111111-1111-1111-1111-111111111111",
                        "produto": "Produto E2E Bloqueado",
                        "valor": "110.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:10:00Z",
                    }
                ],
            },
        )
        assert old_key_resp.status_code == 401, old_key_resp.text

        sync_update_resp = client.post(
            "/sync",
            headers={"X-Empresa-Id": empresa_id, "X-API-Key": rotated_api_key},
            json={
                "empresa_id": empresa_id,
                "records": [
                    {
                        "uuid": "11111111-1111-1111-1111-111111111111",
                        "produto": "Produto E2E Atualizado",
                        "valor": "120.00",
                        "data": "2026-04-24",
                        "data_atualizacao": "2026-04-24T08:20:00Z",
                    }
                ],
            },
        )
        assert sync_update_resp.status_code == 200, sync_update_resp.text
        assert sync_update_resp.json()["inserted_count"] == 0
        assert sync_update_resp.json()["updated_count"] == 1

        clients_summary = client.get(
            "/api/v1/clients/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert clients_summary.status_code == 200, clients_summary.text
        assert clients_summary.json()["total_clients"] == 1
        assert clients_summary.json()["online_clients"] == 1

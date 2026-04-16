import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select


def test_full_flow_sync_and_tenant_isolation() -> None:
    db_path = Path("output/test_integration_sync.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    from backend.main import app
    from backend.config.database import SessionLocal
    from backend.models.venda import Venda

    with TestClient(app) as client:
        create_resp_a = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test"},
            json={"empresa_id": "12345678000199", "nome": "Empresa A"},
        )
        assert create_resp_a.status_code == 200
        api_key_a = create_resp_a.json()["api_key"]

        create_resp_b = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test"},
            json={"empresa_id": "98765432000155", "nome": "Empresa B"},
        )
        assert create_resp_b.status_code == 200
        api_key_b = create_resp_b.json()["api_key"]

        payload_a = {
            "empresa_id": "12345678000199",
            "records": [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "produto": "Produto A",
                    "valor": "100.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T13:00:00Z",
                }
            ],
        }
        sync_resp_a = client.post(
            "/sync",
            headers={"X-Empresa-Id": "12345678000199", "X-API-Key": api_key_a},
            json=payload_a,
        )
        assert sync_resp_a.status_code == 200
        assert sync_resp_a.json()["inserted_count"] == 1
        assert sync_resp_a.json()["updated_count"] == 0

        payload_a_update = {
            "empresa_id": "12345678000199",
            "records": [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "produto": "Produto A (Atualizado)",
                    "valor": "110.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T13:10:00Z",
                }
            ],
        }
        sync_resp_a_update = client.post(
            "/sync",
            headers={"X-Empresa-Id": "12345678000199", "X-API-Key": api_key_a},
            json=payload_a_update,
        )
        assert sync_resp_a_update.status_code == 200
        assert sync_resp_a_update.json()["inserted_count"] == 0
        assert sync_resp_a_update.json()["updated_count"] == 1

        payload_b = {
            "empresa_id": "98765432000155",
            "records": [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "produto": "Produto B",
                    "valor": "200.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T13:20:00Z",
                }
            ],
        }
        sync_resp_b = client.post(
            "/sync",
            headers={"X-Empresa-Id": "98765432000155", "X-API-Key": api_key_b},
            json=payload_b,
        )
        assert sync_resp_b.status_code == 200
        assert sync_resp_b.json()["inserted_count"] == 1

        metrics_resp = client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "sync_batches_total" in metrics_resp.text
        assert 'sync_last_success_epoch{empresa_id="12345678000199"}' in metrics_resp.text

    with SessionLocal() as session:
        count_a = session.scalar(
            select(func.count()).select_from(Venda).where(Venda.empresa_id == "12345678000199")
        )
        count_b = session.scalar(
            select(func.count()).select_from(Venda).where(Venda.empresa_id == "98765432000155")
        )
        venda_a = session.execute(
            select(Venda).where(
                Venda.empresa_id == "12345678000199",
                Venda.uuid == "11111111-1111-1111-1111-111111111111",
            )
        ).scalar_one()

    assert count_a == 1
    assert count_b == 1
    assert venda_a.produto == "Produto A (Atualizado)"

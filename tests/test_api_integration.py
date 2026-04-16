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

        source_create = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers={"X-Admin-Token": "admin-token-test"},
            json={
                "nome": "MariaDB origem",
                "connector_type": "mariadb",
                "sync_interval_minutes": 20,
                "settings": {
                    "host": "127.0.0.1",
                    "port": "3308",
                    "database": "xd",
                },
            },
        )
        assert source_create.status_code == 200, source_create.text
        assert source_create.json()["sync_interval_minutes"] == 20
        source_config_id = source_create.json()["id"]

        destination_create = client.post(
            "/admin/tenants/12345678000199/destination-configs",
            headers={"X-Admin-Token": "admin-token-test"},
            json={
                "nome": "PostgreSQL central",
                "connector_type": "postgresql",
                "settings": {
                    "host": "postgres-central",
                    "port": "5432",
                    "database": "sync",
                },
            },
        )
        assert destination_create.status_code == 200, destination_create.text
        destination_config_id = destination_create.json()["id"]

        source_list = client.get(
            "/admin/tenants/12345678000199/source-configs",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert source_list.status_code == 200
        assert len(source_list.json()) == 1
        assert source_list.json()[0]["settings"]["database"] == "xd"

        source_update = client.put(
            f"/admin/tenants/12345678000199/source-configs/{source_config_id}",
            headers={"X-Admin-Token": "admin-token-test"},
            json={
                "nome": "MariaDB origem principal",
                "settings": {
                    "host": "127.0.0.1",
                    "port": "3308",
                    "database": "xd",
                    "schema": "public",
                },
            },
        )
        assert source_update.status_code == 200, source_update.text
        assert source_update.json()["nome"] == "MariaDB origem principal"
        assert source_update.json()["settings"]["schema"] == "public"

        destination_delete = client.delete(
            f"/admin/tenants/12345678000199/destination-configs/{destination_config_id}",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert destination_delete.status_code == 200, destination_delete.text
        assert destination_delete.json()["status"] == "deleted"

        unsupported_connector = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers={"X-Admin-Token": "admin-token-test"},
            json={
                "nome": "Conector invalido",
                "connector_type": "oracle",
                "settings": {},
            },
        )
        assert unsupported_connector.status_code == 400
        assert unsupported_connector.json()["detail"] == "connector_type nao suportado."

        empty_destination_list = client.get(
            "/admin/tenants/12345678000199/destination-configs",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert empty_destination_list.status_code == 200
        assert empty_destination_list.json() == []

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

import os
import importlib
import sys
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select


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


def test_full_flow_sync_and_tenant_isolation(monkeypatch) -> None:
    db_path = Path("output/test_integration_sync.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    audit_headers = {"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"}

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app
    from backend.config.database import SessionLocal
    from backend.models.venda import Venda
    from backend.models.tenant_source_config import TenantSourceConfig

    with TestClient(app) as client:
        create_resp_a = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "12345678000199", "nome": "Empresa A"},
        )
        assert create_resp_a.status_code == 200
        api_key_a = create_resp_a.json()["api_key"]

        create_resp_b = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "98765432000155", "nome": "Empresa B"},
        )
        assert create_resp_b.status_code == 200
        api_key_b = create_resp_b.json()["api_key"]

        source_create = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers=audit_headers,
            json={
                "nome": "MariaDB origem",
                "connector_type": "mariadb",
                "sync_interval_minutes": 20,
                "settings": {
                    "host": "127.0.0.1",
                    "port": "3308",
                    "database": "xd",
                    "password": "super-secret-password",
                },
            },
        )
        assert source_create.status_code == 200, source_create.text
        assert source_create.json()["sync_interval_minutes"] == 20
        assert source_create.json()["settings"]["host"] == "127.0.0.1"
        assert source_create.json()["settings"]["password"] != "super-secret-password"
        source_config_id = source_create.json()["id"]

        with SessionLocal() as session:
            source_config = session.get(TenantSourceConfig, source_config_id)
            assert source_config is not None
            assert source_config.settings_json != '{"database": "xd", "host": "127.0.0.1", "port": "3308"}'

        destination_create = client.post(
            "/admin/tenants/12345678000199/destination-configs",
            headers=audit_headers,
            json={
                "nome": "PostgreSQL central",
                "connector_type": "postgresql",
                "settings": {
                    "database_url": "postgresql://sync-user:sync-pass@postgres-central:5432/sync",
                },
            },
        )
        assert destination_create.status_code == 200, destination_create.text
        assert (
            destination_create.json()["settings"]["database_url"]
            != "postgresql://sync-user:sync-pass@postgres-central:5432/sync"
        )
        destination_config_id = destination_create.json()["id"]

        source_summary = client.get(
            "/admin/tenants/12345678000199/source-configs/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert source_summary.status_code == 200, source_summary.text
        assert source_summary.json()["scope"] == "source"
        assert source_summary.json()["total_count"] == 1
        assert source_summary.json()["active_count"] == 1
        assert source_summary.json()["connector_types"] == ["mariadb"]

        destination_summary = client.get(
            "/admin/tenants/12345678000199/destination-configs/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert destination_summary.status_code == 200, destination_summary.text
        assert destination_summary.json()["scope"] == "destination"
        assert destination_summary.json()["total_count"] == 1
        assert destination_summary.json()["active_count"] == 1
        assert destination_summary.json()["connector_types"] == ["postgresql"]

        source_list = client.get(
            "/admin/tenants/12345678000199/source-configs",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert source_list.status_code == 200
        assert len(source_list.json()) == 1
        assert source_list.json()[0]["settings"]["database"] == "xd"
        assert source_list.json()[0]["settings"]["password"] != "super-secret-password"

        source_update = client.put(
            f"/admin/tenants/12345678000199/source-configs/{source_config_id}",
            headers=audit_headers,
            json={
                "nome": "MariaDB origem principal",
                "settings": {
                    "host": "127.0.0.1",
                    "port": "3308",
                    "database": "xd",
                    "schema": "public",
                    "api_key": "api-key-123456",
                },
            },
        )
        assert source_update.status_code == 200, source_update.text
        assert source_update.json()["nome"] == "MariaDB origem principal"
        assert source_update.json()["settings"]["schema"] == "public"
        assert source_update.json()["settings"]["api_key"] != "api-key-123456"

        from backend.services.tenant_sync_scheduler import TenantSyncScheduler

        sync_calls: list[str] = []

        def fake_run_source_sync(self, config_id: str) -> None:
            sync_calls.append(config_id)

        monkeypatch.setattr(TenantSyncScheduler, "run_source_sync", fake_run_source_sync)

        source_sync_now = client.post(
            f"/admin/tenants/12345678000199/source-configs/{source_config_id}/sync",
            headers=audit_headers,
        )
        assert source_sync_now.status_code == 200, source_sync_now.text
        assert source_sync_now.json()["id"] == source_config_id
        assert sync_calls == [source_config_id]

        destination_delete = client.delete(
            f"/admin/tenants/12345678000199/destination-configs/{destination_config_id}",
            headers=audit_headers,
        )
        assert destination_delete.status_code == 200, destination_delete.text
        assert destination_delete.json()["status"] == "deleted"

        unsupported_connector = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers=audit_headers,
            json={
                "nome": "Conector invalido",
                "connector_type": "oracle",
                "settings": {},
            },
        )
        assert unsupported_connector.status_code == 400
        assert unsupported_connector.json()["detail"] == "connector_type nao suportado."

        destination_as_source = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers=audit_headers,
            json={
                "nome": "Destino na origem",
                "connector_type": "postgresql",
                "settings": {},
            },
        )
        assert destination_as_source.status_code == 400
        assert destination_as_source.json()["detail"] == "connector_type nao suportado."

        source_as_destination = client.post(
            "/admin/tenants/12345678000199/destination-configs",
            headers=audit_headers,
            json={
                "nome": "Origem no destino",
                "connector_type": "mariadb",
                "settings": {},
            },
        )
        assert source_as_destination.status_code == 400
        assert source_as_destination.json()["detail"] == "connector_type nao suportado."

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
        assert "tenant_destination_delivery_total" in metrics_resp.text
        assert "tenant_destination_last_event_epoch" in metrics_resp.text

        audit_summary = client.get(
            "/admin/tenants/12345678000199/audit/summary",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert audit_summary.status_code == 200, audit_summary.text
        assert audit_summary.json()["empresa_id"] == "12345678000199"
        assert audit_summary.json()["total_count"] >= 5
        assert audit_summary.json()["failure_count"] >= 1
        assert "panel.admin" in audit_summary.json()["actors"]

        audit_events = client.get(
            "/admin/tenants/12345678000199/audit/events",
            headers={"X-Admin-Token": "admin-token-test"},
            params={"limit": 10},
        )
        assert audit_events.status_code == 200, audit_events.text
        actions = {event["action"] for event in audit_events.json()}
        assert "source_config.create" in actions
        assert "destination_config.delete" in actions
        failed_events = [event for event in audit_events.json() if event["status"] == "failure"]
        assert any(event["action"] == "source_config.create" for event in failed_events)
        assert any(event["detail"].get("error") == "connector_type nao suportado." for event in failed_events)

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


def test_admin_source_config_accepts_secure_settings_file_reference() -> None:
    db_path = Path("output/test_integration_settings_ref.db")
    if db_path.exists():
        db_path.unlink()

    secure_settings_path = Path("output/test_secure_source_settings.json")
    secure_settings_path.write_text(
        '{"tenant_a": {"base_url": "https://api.example.local", "endpoint": "/records", "api_key": "super-secret-api-key"}}',
        encoding="utf-8",
    )

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    audit_headers = {"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"}

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app
    from backend.config.database import SessionLocal
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.utils.crypto import decrypt_json

    with TestClient(app) as client:
        create_tenant = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "12345678000199", "nome": "Empresa Arquivo Seguro"},
        )
        assert create_tenant.status_code == 200, create_tenant.text

        source_create = client.post(
            "/admin/tenants/12345678000199/source-configs",
            headers=audit_headers,
            json={
                "nome": "API por arquivo seguro",
                "connector_type": "api",
                "settings": {
                    "settings_file": str(secure_settings_path),
                    "settings_key": "tenant_a",
                },
            },
        )
        assert source_create.status_code == 200, source_create.text
        body = source_create.json()
        assert body["settings"]["settings_file"] == str(secure_settings_path)
        assert body["settings"]["settings_key"] == "tenant_a"

        with SessionLocal() as session:
            config = session.get(TenantSourceConfig, body["id"])
            assert config is not None
            persisted = decrypt_json(config.settings_json)
            assert persisted["settings_file"] == str(secure_settings_path)
            assert persisted["settings_key"] == "tenant_a"
            assert "api_key" not in persisted


def test_admin_secure_config_creates_reference_and_generates_server_key() -> None:
    db_path = Path("output/test_secure_config_create.db")
    if db_path.exists():
        db_path.unlink()

    secrets_file = Path("output/test_secure_connection_registry.json")
    if secrets_file.exists():
        secrets_file.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["CONNECTION_SECRETS_FILE"] = str(secrets_file)
    audit_headers = {"X-Admin-Token": "admin-token-test", "X-Audit-Actor": "panel.admin"}

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app
    from backend.config.database import SessionLocal
    from backend.models.tenant_source_config import TenantSourceConfig
    from backend.utils.crypto import decrypt_json

    with TestClient(app) as client:
        create_tenant = client.post(
            "/admin/tenants",
            headers=audit_headers,
            json={"empresa_id": "12345678000199", "nome": "Empresa Segura"},
        )
        assert create_tenant.status_code == 200, create_tenant.text

        response = client.post(
            "/admin/tenants/12345678000199/secure-configs",
            headers=audit_headers,
            json={
                "scope": "source",
                "nome": "API segura",
                "connector_type": "api",
                "sync_interval_minutes": 15,
                "settings": {
                    "endpoint": "/records",
                    "timeout_seconds": "30",
                },
                "secret_settings": {
                    "base_url": "https://api.exemplo.local",
                },
                "generate_access_key": True,
                "access_key_field": "api_key",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scope"] == "source"
        assert body["config"]["connector_type"] == "api"
        assert body["config"]["settings"]["endpoint"] == "/records"
        assert "settings_file" in body["config"]["settings"]
        assert "settings_key" in body["config"]["settings"]
        assert body["generated_access_key"]
        assert body["secrets_file"] == str(secrets_file)

        with SessionLocal() as session:
            config = session.get(TenantSourceConfig, body["config"]["id"])
            assert config is not None
            persisted = decrypt_json(config.settings_json)
            assert persisted["endpoint"] == "/records"
            assert persisted["settings_file"] == str(secrets_file)
            assert persisted["settings_key"] == body["settings_key"]
            assert "base_url" not in persisted
            assert "api_key" not in persisted

    registry_payload = json.loads(secrets_file.read_text(encoding="utf-8"))
    secret_entry = registry_payload[body["settings_key"]]
    assert secret_entry["base_url"] == "https://api.exemplo.local"
    assert secret_entry["api_key"] == body["generated_access_key"]

    with TestClient(app) as client:
        rotate_response = client.post(
            f"/admin/tenants/12345678000199/secure-configs/{body['settings_key']}/rotate-key",
            headers=audit_headers,
            json={"access_key_field": "api_key"},
        )
        assert rotate_response.status_code == 200, rotate_response.text
        rotate_body = rotate_response.json()
        assert rotate_body["settings_key"] == body["settings_key"]
        assert rotate_body["access_key_field"] == "api_key"
        assert rotate_body["generated_access_key"] != body["generated_access_key"]

    rotated_registry_payload = json.loads(secrets_file.read_text(encoding="utf-8"))
    rotated_entry = rotated_registry_payload[body["settings_key"]]
    assert rotated_entry["base_url"] == "https://api.exemplo.local"
    assert rotated_entry["api_key"] == rotate_body["generated_access_key"]

    update_response = client.post(
        f"/admin/tenants/12345678000199/secure-configs/{body['settings_key']}/update-secret",
        headers=audit_headers,
        json={
            "secret_settings": {
                "base_url": "https://api-rotacionada.exemplo.local",
                "timeout_header": "45",
            },
            "merge": True,
        },
    )
    assert update_response.status_code == 200, update_response.text
    update_body = update_response.json()
    assert update_body["settings_key"] == body["settings_key"]
    assert update_body["updated_fields"] == ["base_url", "timeout_header"]

    updated_registry_payload = json.loads(secrets_file.read_text(encoding="utf-8"))
    updated_entry = updated_registry_payload[body["settings_key"]]
    assert updated_entry["base_url"] == "https://api-rotacionada.exemplo.local"
    assert updated_entry["timeout_header"] == "45"
    assert updated_entry["api_key"] == rotate_body["generated_access_key"]

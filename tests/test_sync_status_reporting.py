import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient


def _clear_backend_modules() -> None:
    for name in list(sys.modules):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name, None)


def test_sync_status_updates_local_client_last_sync() -> None:
    db_path = Path("output/test_sync_status_reporting.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    _clear_backend_modules()

    from backend.config.database import SessionLocal
    from backend.main import app
    from backend.models.local_client import LocalClient

    with TestClient(app) as client:
        tenant_response = client.post(
            "/admin/tenants",
            headers={"X-Admin-Token": "admin-token-test"},
            json={"empresa_id": "12345678000199", "nome": "Empresa A"},
        )
        assert tenant_response.status_code == 200, tenant_response.text
        api_key = tenant_response.json()["api_key"]

        status_response = client.post(
            "/sync/status",
            headers={
                "X-Empresa-Id": "12345678000199",
                "X-API-Key": api_key,
                "X-Agent-Device-Label": "caixa-principal",
            },
            json={
                "status": "success",
                "last_sync_at": "2026-04-30T20:10:00Z",
                "processed_count": 0,
                "reason": "no_records",
            },
        )

    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["empresa_id"] == "12345678000199"
    assert body["status"] == "ok"

    with SessionLocal() as session:
        stored = session.get(LocalClient, body["client_id"])
        assert stored is not None
        assert stored.empresa_id == "12345678000199"
        assert stored.hostname == "caixa-principal"
        assert stored.last_sync_at == datetime(2026, 4, 30, 20, 10)
        assert "no_records" in stored.last_status_json


def test_sync_runner_reports_status_when_there_are_no_records() -> None:
    from agent_local.sync.checkpoint_store import CheckpointStore
    from agent_local.sync.sync_runner import SyncRunner

    class EmptyMariaDBClient:
        def fetch_changed_vendas(self, *, empresa_id: str, since, limit: int) -> list:
            return []

    class FakeApiClient:
        def __init__(self) -> None:
            self.status_calls = []

        def send_sync_status(self, **kwargs) -> dict:
            self.status_calls.append(kwargs)
            return {"status": "ok"}

    output_dir = Path("output/test_sync_runner_status")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    api_client = FakeApiClient()
    runner = SyncRunner(
        empresa_id="12345678000199",
        mariadb_client=EmptyMariaDBClient(),
        api_client=api_client,
        checkpoint_store=CheckpointStore(str(output_dir / "checkpoints.json")),
        batch_size=500,
        api_key_provider=lambda: "tenant-api-key",
    )

    result = runner.run_once()

    assert result == {"status": "ok", "processed_count": 0}
    assert len(api_client.status_calls) == 1
    assert api_client.status_calls[0]["status"] == "success"
    assert api_client.status_calls[0]["processed_count"] == 0
    assert api_client.status_calls[0]["reason"] == "no_records"

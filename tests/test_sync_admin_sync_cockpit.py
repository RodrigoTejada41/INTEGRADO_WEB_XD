from __future__ import annotations

import os
import sys
from pathlib import Path


def _prepare_sync_admin() -> None:
    db_path = Path(f"output/test_sync_admin_sync_cockpit_{os.getpid()}.db")
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"
    os.environ["LOCAL_CONTROL_TOKEN_FILE"] = f"output/test_sync_admin_sync_cockpit_{os.getpid()}.token.txt"

    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_sync_admin_dashboard_exposes_source_cycle_cockpit(monkeypatch) -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import (
        ControlService,
        ControlSummary,
        SourceCycleSummary,
        SyncJobsSummary,
        TenantObservabilitySummary,
    )

    def fake_fetch_summary(self):
        return ControlSummary(
            api_health="online",
            sync_batches_total=12.0,
            sync_records_inserted_total=300.0,
            sync_records_updated_total=45.0,
            sync_application_failures_total=1.0,
            preflight_connection_errors_total=0.0,
            retention_processed_total=0.0,
            tenant_destination_delivery_total=0.0,
            tenant_destination_delivery_failed_total=0.0,
        )

    def fake_fetch_sync_jobs_summary(self):
        return SyncJobsSummary(
            empresa_id="12345678000199",
            pending_count=1.0,
            processing_count=0.0,
            done_count=5.0,
            dead_letter_count=0.0,
            failed_count=0.0,
        )

    def fake_fetch_tenant_observability(self, empresa_id: str | None = None):
        return TenantObservabilitySummary(
            empresa_id=empresa_id or "12345678000199",
            sync_batches_total=12,
            sync_failures_total=1,
            tenant_scheduler_runs_total=4,
            tenant_queue_processed_total=6,
            tenant_queue_failed_total=0,
            tenant_queue_retried_total=0,
            tenant_queue_dead_letter_total=0,
            tenant_destination_delivery_total=0,
            tenant_destination_delivery_failed_total=0,
            sync_last_success_lag_seconds=120,
            tenant_scheduler_last_success_lag_seconds=180,
            tenant_queue_last_event_lag_seconds=60,
            tenant_destination_last_event_lag_seconds=0,
        )

    source_configs = [
        {
            "id": "src-1",
            "empresa_id": "12345678000199",
            "nome": "Caixa principal",
            "connector_type": "mariadb",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:00:00+00:00",
            "last_scheduled_at": "2026-04-24T10:16:00+00:00",
            "next_run_at": "2026-04-24T10:32:00+00:00",
            "last_status": "ok",
            "last_error": None,
            "settings": {},
        },
        {
            "id": "src-2",
            "empresa_id": "12345678000199",
            "nome": "Filial backup",
            "connector_type": "api",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:10:00+00:00",
            "last_scheduled_at": "2026-04-24T10:26:00+00:00",
            "next_run_at": "2026-04-24T10:20:00+00:00",
            "last_status": "retrying",
            "last_error": "timeout",
            "settings": {},
        },
    ]

    cycle_calls: list[list[dict]] = []

    def fake_fetch_source_configs(self):
        return source_configs

    def fake_fetch_sync_jobs(self, limit: int = 20):
        return [
            {
                "id": "job-1",
                "empresa_id": "12345678000199",
                "source_config_id": "src-1",
                "status": "queued",
                "attempts": 0,
                "scheduled_at": "2026-04-24T10:15:00+00:00",
                "next_run_at": "2026-04-24T10:32:00+00:00",
                "started_at": None,
                "finished_at": None,
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:15:00+00:00",
                "updated_at": "2026-04-24T10:15:00+00:00",
            },
            {
                "id": "job-2",
                "empresa_id": "12345678000199",
                "source_config_id": "src-2",
                "status": "done",
                "attempts": 1,
                "scheduled_at": "2026-04-24T10:10:00+00:00",
                "next_run_at": "2026-04-24T10:26:00+00:00",
                "started_at": "2026-04-24T10:11:00+00:00",
                "finished_at": "2026-04-24T10:12:00+00:00",
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:10:00+00:00",
                "updated_at": "2026-04-24T10:12:00+00:00",
            },
        ]

    def fake_fetch_sync_jobs(self, limit: int = 20):
        return [
            {
                "id": "job-1",
                "empresa_id": "12345678000199",
                "source_config_id": "src-1",
                "status": "processing",
                "attempts": 1,
                "scheduled_at": "2026-04-24T10:15:00+00:00",
                "next_run_at": "2026-04-24T10:32:00+00:00",
                "started_at": "2026-04-24T10:16:00+00:00",
                "finished_at": None,
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:15:00+00:00",
                "updated_at": "2026-04-24T10:16:00+00:00",
            },
            {
                "id": "job-2",
                "empresa_id": "12345678000199",
                "source_config_id": "src-2",
                "status": "done",
                "attempts": 1,
                "scheduled_at": "2026-04-24T10:10:00+00:00",
                "next_run_at": "2026-04-24T10:26:00+00:00",
                "started_at": "2026-04-24T10:11:00+00:00",
                "finished_at": "2026-04-24T10:12:00+00:00",
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:10:00+00:00",
                "updated_at": "2026-04-24T10:12:00+00:00",
            },
        ]

    def fake_fetch_source_cycle_summary(self, payload=None):
        cycle_calls.append(list(payload or []))
        return SourceCycleSummary(
            empresa_id="12345678000199",
            total_count=2,
            active_count=2,
            due_count=1,
            overdue_count=1,
            next_run_at="2026-04-24T10:20:00+00:00",
            last_success_at="2026-04-24T10:00:00+00:00",
            last_success_lag_seconds=120.0,
        )

    monkeypatch.setattr(ControlService, "fetch_summary", fake_fetch_summary)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs_summary", fake_fetch_sync_jobs_summary)
    monkeypatch.setattr(ControlService, "fetch_tenant_observability", fake_fetch_tenant_observability)
    monkeypatch.setattr(ControlService, "fetch_source_configs", fake_fetch_source_configs)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs", fake_fetch_sync_jobs)
    monkeypatch.setattr(ControlService, "fetch_source_cycle_summary", fake_fetch_source_cycle_summary)
    monkeypatch.setattr(ControlService, "fetch_destination_configs", lambda self: [])
    monkeypatch.setattr(ControlService, "recent_agent_errors", lambda self, limit=20: [])
    monkeypatch.setattr(ControlService, "fetch_dead_letter_jobs", lambda self, limit=10: [])
    monkeypatch.setattr(
        ControlService,
        "api_error_snapshot",
        lambda self: {
            "timestamp": "-",
            "source": "api",
            "event": "sync_application_failures_total",
            "detail": "current_value=1.0",
        },
    )

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        dashboard_page = client.get("/dashboard")
        assert dashboard_page.status_code == 200
        assert "Ciclo de sincronizacao por fonte" in dashboard_page.text
        assert "Caixa principal" in dashboard_page.text
        assert "Filial backup" in dashboard_page.text
        assert "2026-04-24T10:20:00+00:00" in dashboard_page.text
        assert "Fontes ativas" in dashboard_page.text
        assert "Sincronizar todas as fontes" in dashboard_page.text
        assert "/dashboard/source-configs/sync-all" in dashboard_page.text
        assert "running" in dashboard_page.text
        assert "done" in dashboard_page.text
        assert "source-live-status-src-1" in dashboard_page.text

        dashboard_data = client.get("/dashboard/data")
        assert dashboard_data.status_code == 200
        payload = dashboard_data.json()
        assert payload["source_cycle"]["active_count"] == 2
        assert payload["source_cycle"]["due_count"] == 1
        assert payload["source_configs"][0]["last_scheduled_at"] == "2026-04-24T10:16:00+00:00"
        assert payload["sync_jobs"][0]["status"] == "processing"
        assert payload["source_status_snapshot"]["src-1"]["live_status"] == "running"

    assert cycle_calls
    assert len(cycle_calls[0]) == 2


def test_sync_admin_dashboard_triggers_source_sync_action(monkeypatch) -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import (
        ControlService,
        ControlSummary,
        SourceCycleSummary,
        SyncJobsSummary,
        TenantObservabilitySummary,
    )

    source_configs = [
        {
            "id": "src-1",
            "empresa_id": "12345678000199",
            "nome": "Caixa principal",
            "connector_type": "mariadb",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:00:00+00:00",
            "last_scheduled_at": "2026-04-24T10:16:00+00:00",
            "next_run_at": "2026-04-24T10:32:00+00:00",
            "last_status": "ok",
            "last_error": None,
            "settings": {},
        }
    ]

    def fake_fetch_summary(self):
        return ControlSummary(
            api_health="online",
            sync_batches_total=12.0,
            sync_records_inserted_total=300.0,
            sync_records_updated_total=45.0,
            sync_application_failures_total=1.0,
            preflight_connection_errors_total=0.0,
            retention_processed_total=0.0,
            tenant_destination_delivery_total=0.0,
            tenant_destination_delivery_failed_total=0.0,
        )

    def fake_fetch_sync_jobs_summary(self):
        return SyncJobsSummary(
            empresa_id="12345678000199",
            pending_count=1.0,
            processing_count=0.0,
            done_count=5.0,
            dead_letter_count=0.0,
            failed_count=0.0,
        )

    def fake_fetch_tenant_observability(self, empresa_id: str | None = None):
        return TenantObservabilitySummary(
            empresa_id=empresa_id or "12345678000199",
            sync_batches_total=12,
            sync_failures_total=1,
            tenant_scheduler_runs_total=4,
            tenant_queue_processed_total=6,
            tenant_queue_failed_total=0,
            tenant_queue_retried_total=0,
            tenant_queue_dead_letter_total=0,
            tenant_destination_delivery_total=0,
            tenant_destination_delivery_failed_total=0,
            sync_last_success_lag_seconds=120,
            tenant_scheduler_last_success_lag_seconds=180,
            tenant_queue_last_event_lag_seconds=60,
            tenant_destination_last_event_lag_seconds=0,
        )

    def fake_fetch_source_configs(self):
        return source_configs

    def fake_fetch_sync_jobs(self, limit: int = 20):
        return [
            {
                "id": "job-1",
                "empresa_id": "12345678000199",
                "source_config_id": "src-1",
                "status": "queued",
                "attempts": 0,
                "scheduled_at": "2026-04-24T10:15:00+00:00",
                "next_run_at": "2026-04-24T10:32:00+00:00",
                "started_at": None,
                "finished_at": None,
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:15:00+00:00",
                "updated_at": "2026-04-24T10:15:00+00:00",
            },
            {
                "id": "job-2",
                "empresa_id": "12345678000199",
                "source_config_id": "src-2",
                "status": "done",
                "attempts": 1,
                "scheduled_at": "2026-04-24T10:10:00+00:00",
                "next_run_at": "2026-04-24T10:26:00+00:00",
                "started_at": "2026-04-24T10:11:00+00:00",
                "finished_at": "2026-04-24T10:12:00+00:00",
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:10:00+00:00",
                "updated_at": "2026-04-24T10:12:00+00:00",
            },
        ]

    def fake_fetch_source_cycle_summary(self, payload=None):
        return SourceCycleSummary(
            empresa_id="12345678000199",
            total_count=1,
            active_count=1,
            due_count=0,
            overdue_count=0,
            next_run_at="2026-04-24T10:32:00+00:00",
            last_success_at="2026-04-24T10:00:00+00:00",
            last_success_lag_seconds=120.0,
        )

    sync_calls: list[tuple[str, str | None, str | None]] = []

    def fake_trigger_source_sync(self, config_id: str, *, empresa_id: str | None = None, actor: str | None = None):
        sync_calls.append((config_id, empresa_id, actor))
        return {
            "id": config_id,
            "empresa_id": empresa_id or "12345678000199",
            "nome": "Caixa principal",
            "connector_type": "mariadb",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:00:00+00:00",
            "last_scheduled_at": "2026-04-24T10:16:00+00:00",
            "next_run_at": "2026-04-24T10:32:00+00:00",
            "last_status": "queued",
            "last_error": None,
        }

    monkeypatch.setattr(ControlService, "fetch_summary", fake_fetch_summary)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs_summary", fake_fetch_sync_jobs_summary)
    monkeypatch.setattr(ControlService, "fetch_tenant_observability", fake_fetch_tenant_observability)
    monkeypatch.setattr(ControlService, "fetch_source_configs", fake_fetch_source_configs)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs", fake_fetch_sync_jobs)
    monkeypatch.setattr(ControlService, "fetch_source_cycle_summary", fake_fetch_source_cycle_summary)
    monkeypatch.setattr(ControlService, "fetch_destination_configs", lambda self: [])
    monkeypatch.setattr(ControlService, "recent_agent_errors", lambda self, limit=20: [])
    monkeypatch.setattr(ControlService, "fetch_dead_letter_jobs", lambda self, limit=10: [])
    monkeypatch.setattr(ControlService, "trigger_source_sync", fake_trigger_source_sync)
    monkeypatch.setattr(
        ControlService,
        "api_error_snapshot",
        lambda self: {
            "timestamp": "-",
            "source": "api",
            "event": "sync_application_failures_total",
            "detail": "current_value=1.0",
        },
    )

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        dashboard_page = client.get("/dashboard")
        assert dashboard_page.status_code == 200
        assert "Sincronizar agora" in dashboard_page.text
        assert "/dashboard/source-configs/src-1/sync" in dashboard_page.text

        sync_resp = client.post(
            "/dashboard/source-configs/src-1/sync",
            follow_redirects=False,
        )
        assert sync_resp.status_code in (302, 303)
        assert sync_resp.headers["location"].startswith("/dashboard?flash=")
        assert sync_calls == [("src-1", "12345678000199", "admin")]
        sync_calls.clear()

        sync_page = client.post(
            "/dashboard/source-configs/src-1/sync",
            follow_redirects=True,
        )
        assert sync_page.status_code == 200
        assert "Sincronizacao da fonte enfileirada" in sync_page.text

    assert sync_calls == [("src-1", "12345678000199", "admin")]


def test_sync_admin_dashboard_triggers_all_source_sync_action(monkeypatch) -> None:
    _prepare_sync_admin()

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.control_service import (
        ControlService,
        ControlSummary,
        SourceCycleSummary,
        SyncJobsSummary,
        TenantObservabilitySummary,
    )

    source_configs = [
        {
            "id": "src-1",
            "empresa_id": "12345678000199",
            "nome": "Caixa principal",
            "connector_type": "mariadb",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:00:00+00:00",
            "last_scheduled_at": "2026-04-24T10:16:00+00:00",
            "next_run_at": "2026-04-24T10:32:00+00:00",
            "last_status": "ok",
            "last_error": None,
            "settings": {},
        },
        {
            "id": "src-2",
            "empresa_id": "12345678000199",
            "nome": "Filial backup",
            "connector_type": "api",
            "sync_interval_minutes": 16,
            "ativo": True,
            "last_run_at": "2026-04-24T10:10:00+00:00",
            "last_scheduled_at": "2026-04-24T10:26:00+00:00",
            "next_run_at": "2026-04-24T10:20:00+00:00",
            "last_status": "retrying",
            "last_error": "timeout",
            "settings": {},
        },
    ]

    def fake_fetch_summary(self):
        return ControlSummary(
            api_health="online",
            sync_batches_total=12.0,
            sync_records_inserted_total=300.0,
            sync_records_updated_total=45.0,
            sync_application_failures_total=1.0,
            preflight_connection_errors_total=0.0,
            retention_processed_total=0.0,
            tenant_destination_delivery_total=0.0,
            tenant_destination_delivery_failed_total=0.0,
        )

    def fake_fetch_sync_jobs_summary(self):
        return SyncJobsSummary(
            empresa_id="12345678000199",
            pending_count=1.0,
            processing_count=0.0,
            done_count=5.0,
            dead_letter_count=0.0,
            failed_count=0.0,
        )

    def fake_fetch_tenant_observability(self, empresa_id: str | None = None):
        return TenantObservabilitySummary(
            empresa_id=empresa_id or "12345678000199",
            sync_batches_total=12,
            sync_failures_total=1,
            tenant_scheduler_runs_total=4,
            tenant_queue_processed_total=6,
            tenant_queue_failed_total=0,
            tenant_queue_retried_total=0,
            tenant_queue_dead_letter_total=0,
            tenant_destination_delivery_total=0,
            tenant_destination_delivery_failed_total=0,
            sync_last_success_lag_seconds=120,
            tenant_scheduler_last_success_lag_seconds=180,
            tenant_queue_last_event_lag_seconds=60,
            tenant_destination_last_event_lag_seconds=0,
        )

    def fake_fetch_source_configs(self):
        return source_configs

    def fake_fetch_sync_jobs(self, limit: int = 20):
        return [
            {
                "id": "job-1",
                "empresa_id": "12345678000199",
                "source_config_id": "src-1",
                "status": "queued",
                "attempts": 0,
                "scheduled_at": "2026-04-24T10:15:00+00:00",
                "next_run_at": "2026-04-24T10:32:00+00:00",
                "started_at": None,
                "finished_at": None,
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:15:00+00:00",
                "updated_at": "2026-04-24T10:15:00+00:00",
            },
            {
                "id": "job-2",
                "empresa_id": "12345678000199",
                "source_config_id": "src-2",
                "status": "done",
                "attempts": 1,
                "scheduled_at": "2026-04-24T10:10:00+00:00",
                "next_run_at": "2026-04-24T10:26:00+00:00",
                "started_at": "2026-04-24T10:11:00+00:00",
                "finished_at": "2026-04-24T10:12:00+00:00",
                "dead_letter_at": None,
                "dead_letter_reason": None,
                "last_error": None,
                "created_at": "2026-04-24T10:10:00+00:00",
                "updated_at": "2026-04-24T10:12:00+00:00",
            },
        ]

    def fake_fetch_source_cycle_summary(self, payload=None):
        return SourceCycleSummary(
            empresa_id="12345678000199",
            total_count=2,
            active_count=2,
            due_count=1,
            overdue_count=1,
            next_run_at="2026-04-24T10:20:00+00:00",
            last_success_at="2026-04-24T10:00:00+00:00",
            last_success_lag_seconds=120.0,
        )

    sync_all_calls: list[str] = []

    def fake_trigger_all_source_sync(self, empresa_id: str | None = None, actor: str | None = None):
        sync_all_calls.append(empresa_id or "12345678000199")
        return {
            "empresa_id": empresa_id or "12345678000199",
            "scope": "source",
            "total_count": 2,
            "active_count": 2,
            "inactive_count": 0,
            "pending_count": 1,
            "ok_count": 1,
            "failed_count": 0,
            "retrying_count": 1,
            "dead_letter_count": 0,
            "connector_types": ["mariadb", "api"],
        }

    monkeypatch.setattr(ControlService, "fetch_summary", fake_fetch_summary)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs_summary", fake_fetch_sync_jobs_summary)
    monkeypatch.setattr(ControlService, "fetch_tenant_observability", fake_fetch_tenant_observability)
    monkeypatch.setattr(ControlService, "fetch_source_configs", fake_fetch_source_configs)
    monkeypatch.setattr(ControlService, "fetch_sync_jobs", fake_fetch_sync_jobs)
    monkeypatch.setattr(ControlService, "fetch_source_cycle_summary", fake_fetch_source_cycle_summary)
    monkeypatch.setattr(ControlService, "fetch_destination_configs", lambda self: [])
    monkeypatch.setattr(ControlService, "recent_agent_errors", lambda self, limit=20: [])
    monkeypatch.setattr(ControlService, "fetch_dead_letter_jobs", lambda self, limit=10: [])
    monkeypatch.setattr(ControlService, "trigger_all_source_sync", fake_trigger_all_source_sync)
    monkeypatch.setattr(
        ControlService,
        "api_error_snapshot",
        lambda self: {
            "timestamp": "-",
            "source": "api",
            "event": "sync_application_failures_total",
            "detail": "current_value=1.0",
        },
    )

    with TestClient(app) as client:
        login_resp = client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=False,
        )
        assert login_resp.status_code in (302, 303)

        dashboard_page = client.get("/dashboard")
        assert dashboard_page.status_code == 200
        assert "Sincronizar todas as fontes" in dashboard_page.text
        assert "/dashboard/source-configs/sync-all" in dashboard_page.text
        assert "queued" in dashboard_page.text
        assert "done" in dashboard_page.text
        assert "source-live-status-src-1" in dashboard_page.text

        sync_resp = client.post(
            "/dashboard/source-configs/sync-all",
            follow_redirects=False,
        )
        assert sync_resp.status_code in (302, 303)
        assert sync_resp.headers["location"].startswith("/dashboard?flash=")
        assert sync_all_calls == ["12345678000199"]
        sync_all_calls.clear()

        sync_page = client.post(
            "/dashboard/source-configs/sync-all",
            follow_redirects=True,
        )
        assert sync_page.status_code == 200
        assert "Sincronizacao de 2 fontes ativas enfileiradas" in sync_page.text

    assert sync_all_calls == ["12345678000199"]

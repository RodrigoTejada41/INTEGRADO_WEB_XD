from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def _reset_backend() -> None:
    for module_name in [
        "backend.main",
        "backend.api.routes",
        "backend.api.routes.health",
        "backend.api.routes.metrics",
        "backend.config.database",
        "backend.config.settings",
    ]:
        sys.modules.pop(module_name, None)

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()


def test_metrics_and_request_headers_are_exposed() -> None:
    db_path = Path("output/test_observability.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    _reset_backend()

    from backend.main import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ok"
        assert "components" in response.json()
        assert "X-Request-Id" in response.headers
        assert "X-Correlation-Id" in response.headers
        assert "X-Response-Time-ms" in response.headers

        live = client.get("/health/live")
        assert live.status_code == 200, live.text
        assert live.json()["status"] == "live"

        ready = client.get("/health/ready")
        assert ready.status_code == 200, ready.text
        assert ready.json()["status"] == "ready"
        assert ready.json()["components"]["database"] == "ready"
        assert ready.json()["components"]["memory_database"] == "ready"

        metrics = client.get("/metrics")
        assert metrics.status_code == 200, metrics.text
        assert "http_requests_total" in metrics.text
        assert "app_uptime_seconds" in metrics.text
        assert "tenant_sync_batches_total" in metrics.text

    os.environ.pop("RATE_LIMIT_ENABLED", None)


def test_rate_limit_blocks_excess_requests() -> None:
    db_path = Path("output/test_rate_limit.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "1"

    _reset_backend()

    from backend.main import app

    with TestClient(app) as client:
        first = client.get("/health")
        assert first.status_code == 200, first.text
        second = client.get("/health")
        assert second.status_code == 429, second.text
        assert second.json()["detail"] == "Rate limit excedido."

    os.environ.pop("RATE_LIMIT_ENABLED", None)
    os.environ.pop("RATE_LIMIT_REQUESTS_PER_MINUTE", None)

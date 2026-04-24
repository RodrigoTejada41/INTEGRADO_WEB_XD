from __future__ import annotations

import importlib
import os
import socket
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient

SYNC_ADMIN_ROOT = Path("sync-admin").resolve()
if str(SYNC_ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SYNC_ADMIN_ROOT))

from app.core.db import Base as SyncAdminBase
from app.services.remote_agent_service import RemoteAgentService


def _reset_backend_modules() -> None:
    prefixes = ("backend.api", "backend.config", "backend.main", "backend.services", "backend.repositories")
    for module_name in list(sys.modules):
        if module_name == "backend.main" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


def _reset_sync_admin_modules() -> None:
    prefixes = ("app.",)
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


@contextmanager
def _stub_health_server() -> str:
    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health/ready":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ready"}')
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()

    server = ThreadingHTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _sync_admin_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    SyncAdminBase.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
    return factory()


def test_backend_and_sync_admin_expose_production_readiness(tmp_path: Path) -> None:
    backend_db = tmp_path / "production_readiness_backend.db"
    memory_db = tmp_path / "production_readiness_memory.db"
    sync_db = tmp_path / "production_readiness_sync_admin.db"

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{backend_db.as_posix()}"
    os.environ["MEMORY_DATABASE_URL"] = f"sqlite+pysqlite:///{memory_db.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "production-admin-token"
    os.environ["SECRET_KEY"] = "production-backend-secret"
    os.environ["ENVIRONMENT"] = "production"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    _reset_backend_modules()
    import backend.config.settings as backend_settings_module

    backend_settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    try:
        from backend.main import app as backend_app

        with TestClient(backend_app) as client:
            health = client.get("/health")
            assert health.status_code == 200, health.text
            assert health.json()["status"] == "ok"

            live = client.get("/health/live")
            assert live.status_code == 200, live.text
            assert live.json()["status"] == "live"

            ready = client.get("/health/ready")
            assert ready.status_code == 200, ready.text
            assert ready.json()["status"] == "ready"
            assert ready.json()["components"]["database"] == "ready"
            assert ready.json()["components"]["memory_database"] == "ready"
            assert ready.json()["components"]["scheduler"] == "ready"

        with _stub_health_server() as control_api_base_url:
            os.environ["APP_ENV"] = "production"
            os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{sync_db.as_posix()}"
            os.environ["SECRET_KEY"] = "production-sync-admin-secret"
            os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
            os.environ["INITIAL_ADMIN_PASSWORD"] = "production-admin-password"
            os.environ["INTEGRATION_API_KEY"] = "production-sync-key"
            os.environ["CONTROL_ADMIN_TOKEN"] = "production-control-token"
            os.environ["CONTROL_API_BASE_URL"] = control_api_base_url
            os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
            os.environ["LOCAL_CONTROL_TOKEN"] = "production-local-token"

            sync_admin_root = Path("sync-admin").resolve()
            if str(sync_admin_root) not in sys.path:
                sys.path.insert(0, str(sync_admin_root))

            _reset_sync_admin_modules()
            importlib.invalidate_caches()

            from app.main import app as sync_admin_app

            with TestClient(sync_admin_app) as client:
                health = client.get("/health")
                assert health.status_code == 200, health.text
                assert health.json()["status"] == "online"

                live = client.get("/health/live")
                assert live.status_code == 200, live.text
                assert live.json()["status"] == "live"

                ready = client.get("/health/ready")
                assert ready.status_code == 200, ready.text
                assert ready.json()["status"] == "ready"
                assert ready.json()["components"]["database"] == "ready"
                assert ready.json()["components"]["control_api"] == "ready"

            remote_agent_session = _sync_admin_session()
            remote_agent_service = RemoteAgentService(remote_agent_session)
            remote_agent_snapshot = remote_agent_service.build_status_snapshot()

            assert remote_agent_snapshot["service"] == "sync-admin"
            assert "last_command_poll_at" in remote_agent_snapshot
            assert "last_registration_at" in remote_agent_snapshot
            assert "pending_local_batches" in remote_agent_snapshot
            assert "total_local_records" in remote_agent_snapshot

            remote_agent_session.close()
    finally:
        _reset_backend_modules()
        _reset_sync_admin_modules()
        for module_name in [
            "backend.main",
            "backend.api",
            "backend.config",
            "backend.services",
            "backend.repositories",
            "app.main",
            "app.api",
            "app.config",
            "app.core",
            "app.services",
            "app.web",
        ]:
            sys.modules.pop(module_name, None)
        importlib.invalidate_caches()

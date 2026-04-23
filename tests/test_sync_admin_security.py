from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest


SYNC_ADMIN_ROOT = Path("sync-admin").resolve()


def _reset_sync_admin_modules() -> None:
    prefixes = ("app.",)
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


def _load_sync_admin_app(tmp_path: Path, app_env: str) -> object:
    os.environ["APP_ENV"] = app_env
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{(tmp_path / f'sync_admin_{app_env}.db').as_posix()}"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "test-admin-password"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-test-production"
    os.environ["CONTROL_ADMIN_TOKEN"] = "control-token-test-production"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"

    if str(SYNC_ADMIN_ROOT) not in sys.path:
        sys.path.insert(0, str(SYNC_ADMIN_ROOT))

    _reset_sync_admin_modules()
    importlib.invalidate_caches()

    from app.main import app

    return app


def test_sync_admin_enables_secure_sessions_in_production(tmp_path: Path) -> None:
    app = _load_sync_admin_app(tmp_path, "production")
    session_middleware = next(m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware")
    assert session_middleware.kwargs["https_only"] is True


def test_sync_admin_rejects_placeholder_secrets_in_production(tmp_path: Path) -> None:
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{(tmp_path / 'sync_admin_placeholder.db').as_posix()}"
    os.environ["SECRET_KEY"] = "change-me-super-secret"
    os.environ["INITIAL_ADMIN_USERNAME"] = "admin"
    os.environ["INITIAL_ADMIN_PASSWORD"] = "admin123"
    os.environ["INTEGRATION_API_KEY"] = "sync-key-change-me"
    os.environ["CONTROL_ADMIN_TOKEN"] = "change-this-admin-token"
    os.environ["REMOTE_COMMAND_PULL_ENABLED"] = "false"
    os.environ["LOCAL_CONTROL_TOKEN"] = "local-token-test"

    if str(SYNC_ADMIN_ROOT) not in sys.path:
        sys.path.insert(0, str(SYNC_ADMIN_ROOT))

    _reset_sync_admin_modules()
    importlib.invalidate_caches()

    with pytest.raises(ValueError, match="must be set to a non-placeholder value in production"):
        __import__("app.config.settings")

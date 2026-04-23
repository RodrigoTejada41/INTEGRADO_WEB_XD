from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def _reset_backend_modules() -> None:
    prefixes = (
        "backend.api",
        "backend.config",
        "backend.main",
        "backend.services",
        "backend.repositories",
    )
    for module_name in list(sys.modules):
        if module_name == "backend.main" or module_name.startswith(prefixes):
            sys.modules.pop(module_name, None)


def _load_backend_app(tmp_path: Path, environment: str | None) -> object:
    db_path = tmp_path / f"backend_security_{environment or 'default'}.db"

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["AUTO_CREATE_TABLES"] = "false"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    if environment is None:
        os.environ.pop("ENVIRONMENT", None)
    else:
        os.environ["ENVIRONMENT"] = environment

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app

    return app


def test_backend_defaults_to_development_mode(tmp_path: Path) -> None:
    app = _load_backend_app(tmp_path, None)
    session_middleware = next(m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware")
    assert session_middleware.kwargs["https_only"] is False


def test_backend_enables_secure_sessions_in_production(tmp_path: Path) -> None:
    app = _load_backend_app(tmp_path, "production")
    session_middleware = next(m for m in app.user_middleware if m.cls.__name__ == "SessionMiddleware")
    assert session_middleware.kwargs["https_only"] is True

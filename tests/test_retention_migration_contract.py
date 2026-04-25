from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _reset_backend_modules() -> None:
    for module_name in [
        "backend.config.settings",
        "backend.db.migration_runner",
        "backend.db.migrations",
        "backend.schemas.server_settings",
    ]:
        sys.modules.pop(module_name, None)
    importlib.invalidate_caches()


def test_retention_defaults_and_migration_baseline_are_aligned() -> None:
    os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["SECRET_KEY"] = "secret-key-test"
    _reset_backend_modules()

    from backend.config.settings import Settings
    from backend.db.migrations import list_migrations
    from backend.schemas.server_settings import ServerSettingsUpdateRequest

    settings = Settings()
    server_settings = ServerSettingsUpdateRequest()
    migrations = list(list_migrations())

    assert settings.retention_months == 14
    assert settings.retention_mode == "archive"
    assert server_settings.retention_months == 14
    assert server_settings.retention_mode == "archive"
    assert [migration.version for migration in migrations] == [1, 2, 3, 4]


def test_retention_runbook_mentions_14_month_policy() -> None:
    runbook = (ROOT / "infra" / "RUNBOOK_PRODUCAO.md").read_text(encoding="utf-8")
    settings_doc = (ROOT / "infra" / "VPS_DEPLOY.md").read_text(encoding="utf-8")

    assert "14 meses" in runbook or "14 meses" in settings_doc
    assert "archive" in runbook or "archive" in settings_doc

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient


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


def test_memory_api_upsert_and_read_with_db_json_sync() -> None:
    integration_db = Path("output/test_memory_api_integration.db")
    memory_db = Path("output/test_memory_api_cerebro.db")
    memory_json = Path("output/test_memory_api_memory.json")
    for path in (integration_db, memory_db, memory_json):
        if path.exists():
            path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{integration_db.as_posix()}"
    os.environ["MEMORY_DATABASE_URL"] = f"sqlite+pysqlite:///{memory_db.as_posix()}"
    os.environ["MEMORY_JSON_BACKUP_PATH"] = memory_json.as_posix()
    os.environ["ADMIN_TOKEN"] = "admin-token-test"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["RETENTION_JOB_ENABLED"] = "false"

    _reset_backend_modules()

    import backend.config.settings as settings_module

    settings_module.get_settings.cache_clear()
    importlib.invalidate_caches()

    from backend.main import app

    payload = {
        "project_tag": "in_xd_main",
        "memory": {
            "project_context": {
                "name": "INTEGRADO_WEB_XD",
                "objectives": ["Sincronizar dados", "Sincronizar dados"],
                "architecture": ["FastAPI", "PostgreSQL"],
            },
            "technical_decisions": ["Use API first", "Use API first"],
            "completed_tasks": ["P15 concluido"],
            "user_preferences": ["Local-first"],
            "known_issues": ["API memory down"],
        },
    }

    with TestClient(app) as client:
        unauthorized = client.get("/api/v1/memory/in_xd_main")
        assert unauthorized.status_code == 401

        upsert = client.post(
            "/api/v1/memory",
            headers={"X-Admin-Token": "admin-token-test"},
            json=payload,
        )
        assert upsert.status_code == 200, upsert.text
        assert upsert.json()["project_tag"] == "in_xd_main"
        assert upsert.json()["source_used"] in {"DB+JSON", "DB", "JSON"}
        assert upsert.json()["memory"]["project_context"]["name"] == "INTEGRADO_WEB_XD"
        assert upsert.json()["memory"]["project_context"]["objectives"] == ["Sincronizar dados"]
        assert upsert.json()["memory"]["technical_decisions"] == ["Use API first"]

        second = client.post(
            "/api/v1/memory",
            headers={"X-Admin-Token": "admin-token-test"},
            json={
                "project_tag": "in_xd_main",
                "memory": {
                    "project_context": {
                        "name": "INTEGRADO_WEB_XD",
                        "objectives": ["Garantir isolamento multi-tenant"],
                        "architecture": ["FastAPI"],
                    },
                    "technical_decisions": ["Use API first", "Fallback DB+JSON"],
                    "completed_tasks": ["P16 iniciado"],
                    "user_preferences": [],
                    "known_issues": ["API memory down"],
                },
            },
        )
        assert second.status_code == 200, second.text

        read = client.get(
            "/api/v1/memory/in_xd_main",
            headers={"X-Admin-Token": "admin-token-test"},
        )
        assert read.status_code == 200, read.text
        response = read.json()
        assert response["project_tag"] == "in_xd_main"
        assert response["memory"]["project_context"]["objectives"] == [
            "Sincronizar dados",
            "Garantir isolamento multi-tenant",
        ]
        assert response["memory"]["technical_decisions"] == [
            "Use API first",
            "Fallback DB+JSON",
        ]
        assert response["memory"]["completed_tasks"] == ["P15 concluido", "P16 iniciado"]

    assert memory_db.exists()
    assert memory_json.exists()
    raw_json = json.loads(memory_json.read_text(encoding="utf-8"))
    assert "in_xd_main" in raw_json["projects"]


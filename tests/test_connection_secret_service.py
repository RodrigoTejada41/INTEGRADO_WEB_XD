from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.config.settings import Settings
from backend.services.connection_secret_service import ConnectionSecretService


class _FakeRepository:
    def __init__(self, secrets_file: str) -> None:
        self._secrets_file = secrets_file

    def get_many(self, keys: list[str]) -> dict[str, str]:
        return {"connection_secrets_file": self._secrets_file}


def _test_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+pysqlite:///output/test_connection_secret_service.db",
        ADMIN_TOKEN="test-admin-token",
    )


def test_connection_secret_service_rejects_invalid_registry_root() -> None:
    secrets_file = Path("output/test_connection_secret_registry_invalid.json")
    if secrets_file.exists():
        secrets_file.unlink()
    secrets_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    service = ConnectionSecretService(_FakeRepository(str(secrets_file)), app_settings=_test_settings())

    with pytest.raises(RuntimeError, match="Registry de segredos invalido"):
        service.rotate_access_key(settings_key="missing")


def test_connection_secret_service_persists_registry_atomically() -> None:
    secrets_file = Path("output/test_connection_secret_registry.json")
    if secrets_file.exists():
        secrets_file.unlink()
    service = ConnectionSecretService(_FakeRepository(str(secrets_file)), app_settings=_test_settings())

    settings_key, written_file, generated_key = service.create_secret_reference(
        secret_settings={"base_url": "https://example.local"},
        generate_access_key=True,
        access_key_field="api_key",
    )

    assert written_file == str(secrets_file)
    assert generated_key is not None
    persisted = json.loads(secrets_file.read_text(encoding="utf-8"))
    assert persisted[settings_key]["base_url"] == "https://example.local"
    assert persisted[settings_key]["api_key"] == generated_key

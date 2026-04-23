from __future__ import annotations

import pytest


def test_backend_sync_config_defaults_to_16() -> None:
    from backend.schemas.secure_connection_configs import SecureConnectionConfigCreateRequest
    from backend.schemas.tenant_configs import TenantConfigCreateRequest

    tenant_request = TenantConfigCreateRequest(nome="Fonte", connector_type="mariadb")
    secure_request = SecureConnectionConfigCreateRequest(
        scope="source",
        nome="Fonte segura",
        connector_type="mariadb",
    )

    assert tenant_request.sync_interval_minutes == 16
    assert secure_request.sync_interval_minutes == 16


def test_agent_sync_interval_defaults_and_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_EMPRESA_ID", "12345678000199")
    monkeypatch.setenv("AGENT_API_BASE_URL", "https://api.example.local/admin/api")
    monkeypatch.setenv("AGENT_API_KEY", "key-test")
    monkeypatch.setenv("AGENT_MARIADB_URL", "mysql+pymysql://root:root@127.0.0.1:3308/xd")
    monkeypatch.delenv("SYNC_INTERVAL_MINUTES", raising=False)

    import agent_local.config.settings as settings_module

    settings_module.get_agent_settings.cache_clear()
    default_settings = settings_module.get_agent_settings()
    assert default_settings.sync_interval_minutes == 16

    monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "18")
    settings_module.get_agent_settings.cache_clear()
    overridden_settings = settings_module.get_agent_settings()
    assert overridden_settings.sync_interval_minutes == 18

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_local import main as agent_main


@dataclass
class _FakeIdentity:
    client_id: str
    token: str
    hostname: str


class _FakeIdentityStore:
    def __init__(self, identity_file: str) -> None:
        self.identity_file = identity_file

    def load_or_create(self) -> _FakeIdentity:
        return _FakeIdentity(
            client_id="client-123",
            token="token-from-store",
            hostname="host-01",
        )


class _FakeApiClient:
    instances: list["_FakeApiClient"] = []

    def __init__(self, base_url: str, empresa_id: str, api_key: str, timeout_seconds: int, verify_ssl: bool) -> None:
        self.base_url = base_url
        self.empresa_id = empresa_id
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl
        self.register_calls: list[dict[str, object]] = []
        self.heartbeat_calls: list[dict[str, object]] = []
        _FakeApiClient.instances.append(self)

    def register_local_client(self, payload: dict, api_key: str | None = None) -> dict:
        self.register_calls.append({"payload": payload, "api_key": api_key})
        return {"status": "registered"}

    def send_heartbeat(self, client_id: str, client_token: str, payload: dict) -> dict:
        self.heartbeat_calls.append(
            {
                "client_id": client_id,
                "client_token": client_token,
                "payload": payload,
            }
        )
        return {"status": "heartbeat_received"}


class _FakeRunner:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def run_once(self) -> dict[str, object]:
        return {"synced": True}


class _FakeHealthcheck:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def run_preflight(self) -> dict[str, object]:
        return {"ok": True, "mariadb_ok": True, "api_ok": True, "errors": []}


class _FakeCheckpointStore:
    def __init__(self, *args, **kwargs) -> None:
        pass


class _FakeMariaDBClient:
    def __init__(self, *args, **kwargs) -> None:
        pass


@dataclass
class _FakeSettings:
    empresa_id: str = "12345678000199"
    api_base_url: str = "https://movisystecnologia.com.br/admin/api"
    api_key: str = ""
    api_key_file: str = "output/test_agent_main_registration/agent_api_key.txt"
    mariadb_url: str = "sqlite:///./output/test_agent_main_registration.db"
    sync_interval_minutes: int = 16
    batch_size: int = 500
    timeout_seconds: int = 30
    verify_ssl: bool = True
    checkpoint_file: str = "output/test_agent_main_registration/checkpoints.json"
    local_client_identity_file: str = "output/test_agent_main_registration/local_client_identity.json"
    log_level: str = "INFO"
    source_query: str | None = None
    audit_file: str | None = None


def test_main_registers_with_api_key_from_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "test_agent_main_registration"
    base_dir.mkdir(parents=True, exist_ok=True)
    settings = _FakeSettings(
        api_key_file=str(base_dir / "agent_api_key.txt"),
        mariadb_url=f"sqlite:///{(base_dir / 'test_agent_main_registration.db').as_posix()}",
        checkpoint_file=str(base_dir / "checkpoints.json"),
        local_client_identity_file=str(base_dir / "local_client_identity.json"),
    )
    Path(settings.api_key_file).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.api_key_file).write_text("key-from-file", encoding="utf-8")

    monkeypatch.setattr(agent_main, "get_agent_settings", lambda: settings)
    monkeypatch.setattr(agent_main, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(agent_main, "MariaDBClient", _FakeMariaDBClient)
    monkeypatch.setattr(agent_main, "SyncApiClient", _FakeApiClient)
    monkeypatch.setattr(agent_main, "CheckpointStore", _FakeCheckpointStore)
    monkeypatch.setattr(agent_main, "LocalClientIdentityStore", _FakeIdentityStore)
    monkeypatch.setattr(agent_main, "SyncRunner", _FakeRunner)
    monkeypatch.setattr(agent_main, "AgentHealthcheck", _FakeHealthcheck)

    def stop_after_first_sleep(_seconds: int) -> None:
        raise SystemExit

    monkeypatch.setattr(agent_main.time, "sleep", stop_after_first_sleep)

    with pytest.raises(SystemExit):
        agent_main.main()

    assert _FakeApiClient.instances, "SyncApiClient nao foi instanciado."
    client = _FakeApiClient.instances[0]
    assert client.register_calls, "Registro inicial nao foi executado."
    assert client.register_calls[0]["api_key"] == "key-from-file"

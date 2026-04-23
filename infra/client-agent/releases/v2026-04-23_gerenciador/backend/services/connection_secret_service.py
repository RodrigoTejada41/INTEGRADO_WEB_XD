from __future__ import annotations

import json
import secrets
from pathlib import Path
from tempfile import NamedTemporaryFile

from backend.config.settings import Settings, get_settings
from backend.repositories.server_setting_repository import ServerSettingRepository


class ConnectionSecretService:
    def __init__(
        self,
        repository: ServerSettingRepository,
        app_settings: Settings | None = None,
    ) -> None:
        self.repository = repository
        self.app_settings = app_settings or get_settings()

    def get_secrets_file(self) -> str:
        current = self.repository.get_many(["connection_secrets_file"])
        return current.get("connection_secrets_file", self.app_settings.connection_secrets_file)

    def create_secret_reference(
        self,
        *,
        secret_settings: dict[str, str],
        generate_access_key: bool = False,
        access_key_field: str | None = None,
    ) -> tuple[str, str, str | None]:
        secrets_file = self.get_secrets_file()
        settings_key = secrets.token_urlsafe(18)
        generated_access_key: str | None = None
        payload = dict(secret_settings)
        if generate_access_key:
            generated_access_key = secrets.token_urlsafe(24)
            payload[access_key_field or "api_key"] = generated_access_key
        self._write_secret_entry(secrets_file=secrets_file, settings_key=settings_key, payload=payload)
        return settings_key, secrets_file, generated_access_key

    def rotate_access_key(
        self,
        *,
        settings_key: str,
        access_key_field: str | None = None,
    ) -> tuple[str, str, str]:
        secrets_file = self.get_secrets_file()
        registry = self._read_registry(secrets_file)
        entry = registry.get(settings_key)
        if not isinstance(entry, dict):
            raise RuntimeError(f"settings_key nao encontrado: {settings_key}")
        resolved_field = self._resolve_access_key_field(entry, access_key_field)
        generated_access_key = secrets.token_urlsafe(24)
        entry[resolved_field] = generated_access_key
        self._write_registry(secrets_file=secrets_file, registry=registry)
        return secrets_file, resolved_field, generated_access_key

    def update_secret_entry(
        self,
        *,
        settings_key: str,
        secret_settings: dict[str, str],
        merge: bool = True,
    ) -> tuple[str, list[str]]:
        secrets_file = self.get_secrets_file()
        registry = self._read_registry(secrets_file)
        entry = registry.get(settings_key)
        if not isinstance(entry, dict):
            raise RuntimeError(f"settings_key nao encontrado: {settings_key}")

        if merge:
            updated_entry = dict(entry)
            updated_entry.update(secret_settings)
        else:
            updated_entry = dict(secret_settings)

        registry[settings_key] = updated_entry
        self._write_registry(secrets_file=secrets_file, registry=registry)
        return secrets_file, sorted(secret_settings.keys())

    def _write_secret_entry(self, *, secrets_file: str, settings_key: str, payload: dict[str, str]) -> None:
        registry = self._read_registry(secrets_file)
        registry[settings_key] = payload
        self._write_registry(secrets_file=secrets_file, registry=registry)

    def _read_registry(self, secrets_file: str) -> dict[str, dict[str, str]]:
        path = Path(secrets_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        registry: dict[str, dict[str, str]] = {}
        if path.exists():
            raw = path.read_text(encoding="utf-8").strip()
            if raw:
                loaded = json.loads(raw)
                if not isinstance(loaded, dict):
                    raise RuntimeError("Registry de segredos invalido: raiz deve ser um objeto JSON.")
                for key, value in loaded.items():
                    if not isinstance(key, str) or not isinstance(value, dict):
                        raise RuntimeError("Registry de segredos invalido: entradas devem ser objetos JSON.")
                    registry[key] = {str(entry_key): str(entry_value) for entry_key, entry_value in value.items()}
        return registry

    def _write_registry(self, *, secrets_file: str, registry: dict[str, dict[str, str]]) -> None:
        path = Path(secrets_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(registry, ensure_ascii=True, indent=2, sort_keys=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
        temp_path.replace(path)

    @staticmethod
    def _resolve_access_key_field(entry: dict[str, str], access_key_field: str | None) -> str:
        if access_key_field:
            return access_key_field
        for candidate in ("api_key", "access_key", "token", "client_token", "local_control_token"):
            if candidate in entry:
                return candidate
        return "api_key"

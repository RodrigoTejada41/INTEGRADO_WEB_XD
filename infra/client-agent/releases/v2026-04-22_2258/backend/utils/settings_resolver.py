from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path


_REFERENCE_KEYS = {"settings_file", "settings_env", "settings_key"}


def _stringify_settings(settings: Mapping[str, object]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in settings.items()
        if value is not None and str(key) not in _REFERENCE_KEYS
    }


def _extract_named_settings(raw: object, settings_key: str | None) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise RuntimeError("conteudo de configuracao deve ser um objeto JSON")
    if not settings_key:
        return raw

    scoped = raw.get(settings_key)
    if not isinstance(scoped, Mapping):
        raise RuntimeError(f"settings_key nao encontrado na configuracao: {settings_key}")
    return scoped


def _load_settings_from_file(file_path: str, settings_key: str | None) -> Mapping[str, object]:
    path = Path(file_path)
    if not path.exists():
        raise RuntimeError(f"arquivo de configuracao inexistente: {path}")
    with path.open("r", encoding="utf-8") as fp:
        content = json.load(fp)
    return _extract_named_settings(content, settings_key)


def _load_settings_from_env(env_name: str, settings_key: str | None) -> Mapping[str, object]:
    raw_value = os.getenv(env_name)
    if not raw_value:
        raise RuntimeError(f"variavel de ambiente nao encontrada: {env_name}")
    try:
        content = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"variavel de ambiente com JSON invalido: {env_name}") from exc
    return _extract_named_settings(content, settings_key)


def resolve_runtime_settings(settings: Mapping[str, object]) -> dict[str, str]:
    settings_file = str(settings.get("settings_file") or "").strip()
    settings_env = str(settings.get("settings_env") or "").strip()
    settings_key = str(settings.get("settings_key") or "").strip() or None

    if settings_file and settings_env:
        raise RuntimeError("use apenas uma referencia de segredo: settings_file ou settings_env")

    resolved: dict[str, str] = {}
    if settings_file:
        resolved.update(_stringify_settings(_load_settings_from_file(settings_file, settings_key)))
    elif settings_env:
        resolved.update(_stringify_settings(_load_settings_from_env(settings_env, settings_key)))

    resolved.update(_stringify_settings(settings))
    return resolved

from __future__ import annotations

import re
from collections.abc import Mapping

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|credential)",
    re.IGNORECASE,
)
_SENSITIVE_EXACT_KEYS = {
    "authorization",
    "connection_string",
    "database_url",
    "dsn",
    "jwt",
    "mariadb_url",
    "uri",
}


def is_sensitive_setting_key(key: str) -> bool:
    normalized = key.strip().lower()
    if normalized in _SENSITIVE_EXACT_KEYS:
        return True
    return bool(_SENSITIVE_KEY_PATTERN.search(normalized))


def mask_secret_value(value: object) -> str:
    text = str(value)
    if not text:
        return ""
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"


def sanitize_settings_for_output(settings: Mapping[str, object]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in settings.items():
        sanitized[key] = mask_secret_value(value) if is_sensitive_setting_key(key) else str(value)
    return sanitized

from __future__ import annotations

import os
from pathlib import Path


def _read_env_file() -> None:
    env_file = Path('.env')
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


def _resolve_sources() -> list[Path]:
    raw = os.getenv('KNOWLEDGE_SOURCE_PATHS', '')
    if raw:
        parts = [p.strip() for p in raw.split(';') if p.strip()]
        if parts:
            return [Path(p).resolve() for p in parts]
    return [Path('input').resolve()]


def _parse_auth_users() -> dict[str, dict[str, str]]:
    raw = os.getenv('AUTH_USERS', '')
    users: dict[str, dict[str, str]] = {}
    if not raw:
        return users
    for entry in raw.split(';'):
        item = entry.strip()
        if not item:
            continue
        parts = item.split(':', 2)
        if len(parts) != 3:
            continue
        username, password, role = parts
        users[username.strip()] = {
            'password': password.strip(),
            'role': role.strip(),
        }
    return users


_read_env_file()

KNOWLEDGE_SOURCE_PATHS = _resolve_sources()
DB_PATH = Path(os.getenv('DB_PATH', 'output/system.db')).resolve()
OBSIDIAN_VAULT_PATH = Path(os.getenv('OBSIDIAN_VAULT_PATH', 'obsidian-vault')).resolve()
NEXUS_MANIFEST_PATH = Path(os.getenv('NEXUS_MANIFEST_PATH', 'nexus-manifests')).resolve()
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8080'))

JWT_SECRET = os.getenv('JWT_SECRET', 'change-me')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_ACCESS_EXPIRES_MINUTES = int(os.getenv('JWT_ACCESS_EXPIRES_MINUTES', os.getenv('JWT_EXPIRES_MINUTES', '60')))
JWT_REFRESH_EXPIRES_MINUTES = int(os.getenv('JWT_REFRESH_EXPIRES_MINUTES', '10080'))
AUTH_USERS = _parse_auth_users()

# Optional ingestion limiter for fast smoke runs. 0 means unlimited.
MAX_FILES_PER_SOURCE = int(os.getenv('MAX_FILES_PER_SOURCE', '0'))

for p in [DB_PATH.parent, OBSIDIAN_VAULT_PATH, NEXUS_MANIFEST_PATH]:
    p.mkdir(parents=True, exist_ok=True)

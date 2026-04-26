from __future__ import annotations

from datetime import UTC, datetime, timedelta
import socket
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import generate_random_api_key, hash_api_key, verify_api_key
from app.repositories.local_runtime_repository import LocalRuntimeRepository


class LocalConfigService:
    PUBLIC_KEYS = {
        'control_api_base_url',
        'local_endpoint_url',
        'sync_interval_minutes',
        'command_poll_interval_seconds',
        'registration_interval_seconds',
        'remote_control_allowed_ips',
    }

    def __init__(self, db: Session):
        self.db = db
        self.repository = LocalRuntimeRepository(db)

    def bootstrap(self) -> None:
        self._ensure_value('installation_id', str(uuid4()))
        self._ensure_value('control_api_base_url', settings.control_api_base_url.rstrip('/'))
        self._ensure_value('local_endpoint_url', settings.local_endpoint_url.rstrip('/'))
        self._ensure_value('sync_interval_minutes', settings.sync_default_interval_minutes)
        self._ensure_value('command_poll_interval_seconds', settings.remote_command_pull_interval_seconds)
        self._ensure_value('registration_interval_seconds', settings.remote_registration_interval_seconds)
        self._ensure_value('remote_control_allowed_ips', self._normalize_ip_list(settings.remote_control_allowed_ips))

        raw_token = self._load_or_create_control_token()
        self.repository.set_value('control_token_hash', hash_api_key(raw_token))
        self.repository.set_value(
            'control_token_expires_at',
            (datetime.now(UTC) + timedelta(days=settings.local_control_token_expiration_days)).isoformat(),
        )
        self.db.commit()

    def get_public_config(self) -> dict[str, object]:
        return {
            'installation_id': self.repository.get_value('installation_id'),
            'empresa_id': settings.control_empresa_id,
            'empresa_nome': settings.control_empresa_nome,
            'control_api_base_url': self.repository.get_value('control_api_base_url'),
            'local_endpoint_url': self.repository.get_value('local_endpoint_url'),
            'sync_interval_minutes': int(self.repository.get_value('sync_interval_minutes', settings.sync_default_interval_minutes)),
            'command_poll_interval_seconds': int(
                self.repository.get_value(
                    'command_poll_interval_seconds',
                    settings.remote_command_pull_interval_seconds,
                )
            ),
            'registration_interval_seconds': int(
                self.repository.get_value(
                    'registration_interval_seconds',
                    settings.remote_registration_interval_seconds,
                )
            ),
            'remote_control_allowed_ips': self.repository.get_value('remote_control_allowed_ips', []),
            'token_expires_at': self.repository.get_value('control_token_expires_at'),
        }

    def update_public_config(self, payload: dict[str, object]) -> dict[str, object]:
        for key, value in payload.items():
            if key not in self.PUBLIC_KEYS or value is None:
                continue
            if key == 'remote_control_allowed_ips':
                self.repository.set_value(key, self._normalize_ip_list(value))
                continue
            self.repository.set_value(key, value)
        self.db.commit()
        return self.get_public_config()

    def verify_control_token(self, raw_token: str, source_ip: str | None = None) -> None:
        token_hash = str(self.repository.get_value('control_token_hash', ''))
        if not raw_token or not token_hash or not verify_api_key(raw_token, token_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid local control token.')

        expires_at = self.repository.get_value('control_token_expires_at')
        if expires_at:
            parsed = datetime.fromisoformat(str(expires_at).replace('Z', '+00:00'))
            parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            if parsed <= datetime.now(UTC):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Expired local control token.')

        whitelist = self.repository.get_value('remote_control_allowed_ips', [])
        if whitelist and source_ip and source_ip not in whitelist:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Source IP not allowed.')

    def current_control_token(self) -> str:
        if settings.local_control_token:
            return settings.local_control_token
        file_path = Path(settings.local_control_token_file)
        if file_path.exists():
            return file_path.read_text(encoding='utf-8').strip()
        raise RuntimeError('Local control token is not available.')

    def record_state(self, key: str, value: object) -> None:
        self.repository.set_value(key, value)
        self.db.commit()

    def hostname(self) -> str:
        return socket.gethostname()

    def installation_id(self) -> str:
        return str(self.repository.get_value('installation_id'))

    @staticmethod
    def _normalize_ip_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def _load_or_create_control_token(self) -> str:
        if settings.local_control_token:
            self._write_control_token_file(settings.local_control_token)
            return settings.local_control_token

        file_path = Path(settings.local_control_token_file)
        if file_path.exists():
            token = file_path.read_text(encoding='utf-8').strip()
            if token:
                return token

        token = generate_random_api_key()
        self._write_control_token_file(token)
        return token

    def _write_control_token_file(self, token: str) -> None:
        file_path = Path(settings.local_control_token_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(token.strip(), encoding='utf-8')

    def _ensure_value(self, key: str, default: object) -> None:
        if self.repository.get(key) is None:
            self.repository.set_value(key, default)

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.correlation import get_correlation_id
from app.models.sync_batch import SyncBatch
from app.models.sync_record import SyncRecord
from app.repositories.remote_command_log_repository import RemoteCommandLogRepository
from app.services.local_config_service import LocalConfigService

logger = logging.getLogger(__name__)


class RemoteAgentService:
    def __init__(self, db: Session):
        self.db = db
        self.config_service = LocalConfigService(db)
        self.command_log_repository = RemoteCommandLogRepository(db)

    def perform_sync_cycle(self, *, reason: str) -> dict[str, object]:
        now = datetime.now(UTC)
        correlation_id = get_correlation_id()
        self.config_service.record_state('last_sync_at', now.isoformat())
        self.config_service.record_state('last_sync_status', 'success')
        self.config_service.record_state('last_sync_reason', reason)
        self.command_log_repository.create(
            command_id=None,
            command_type='force_sync',
            origin=reason,
            status='success',
            detail={'performed_at': now.isoformat(), 'correlation_id': correlation_id},
        )
        self.db.commit()
        return {
            'status': 'success',
            'detail': f'Synchronization cycle recorded for reason={reason}.',
            'last_sync_at': now.isoformat(),
        }

    def build_status_snapshot(self) -> dict[str, object]:
        pending_batches = self.db.scalar(select(func.count()).select_from(SyncBatch)) or 0
        total_records = self.db.scalar(select(func.count()).select_from(SyncRecord)) or 0
        return {
            'service': 'sync-admin',
            'hostname': self.config_service.hostname(),
            'last_sync_at': self.config_service.repository.get_value('last_sync_at'),
            'last_sync_status': self.config_service.repository.get_value('last_sync_status'),
            'last_sync_reason': self.config_service.repository.get_value('last_sync_reason'),
            'last_registration_at': self.config_service.repository.get_value('last_registration_at'),
            'last_command_poll_at': self.config_service.repository.get_value('last_command_poll_at'),
            'last_command_origin': self.config_service.repository.get_value('last_command_origin'),
            'pending_local_batches': int(pending_batches),
            'total_local_records': int(total_records),
        }

    async def run_remote_cycle(self) -> None:
        if not settings.remote_command_pull_enabled:
            return
        try:
            await self.register_if_possible()
            await self.send_heartbeat()
            await self.pull_and_execute_commands()
        except Exception as exc:  # pragma: no cover
            logger.warning('remote_agent_cycle_failed error=%s', str(exc))

    async def register_if_possible(self) -> None:
        tenant_api_key = self._read_tenant_api_key()
        if not tenant_api_key:
            return

        correlation_id = self._next_correlation_id('register')
        public_config = self.config_service.get_public_config()
        payload = {
            'client_id': self.config_service.installation_id(),
            'hostname': self.config_service.hostname(),
            'ip': None,
            'endpoint_url': public_config['local_endpoint_url'],
            'token': self.config_service.current_control_token(),
            'token_expires_at': public_config['token_expires_at'],
            'config_snapshot': public_config,
            'status_snapshot': self.build_status_snapshot(),
        }
        headers = {
            'X-Empresa-Id': settings.control_empresa_id,
            'X-API-Key': tenant_api_key,
            'X-Correlation-Id': correlation_id,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{public_config['control_api_base_url']}/api/v1/register",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        self.config_service.record_state('last_registration_at', datetime.now(UTC).isoformat())

    async def send_heartbeat(self) -> None:
        headers = self._remote_headers(action='heartbeat')
        if headers is None:
            return
        public_config = self.config_service.get_public_config()
        payload = {
            'config_snapshot': public_config,
            'status_snapshot': self.build_status_snapshot(),
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{public_config['control_api_base_url']}/api/v1/clients/me/heartbeat",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

    async def pull_and_execute_commands(self) -> None:
        headers = self._remote_headers(action='poll')
        if headers is None:
            return
        base_url = self.config_service.get_public_config()['control_api_base_url']
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f'{base_url}/api/v1/commands', headers=headers)
            response.raise_for_status()
            commands = response.json()

            self.config_service.record_state('last_command_poll_at', datetime.now(UTC).isoformat())

            for command in commands:
                result_status, result_payload = await self._execute_command(command)
                command_headers = self._remote_headers(
                    action=f"command-result:{command.get('command_type', 'unknown')}"
                )
                if command_headers is None:
                    continue
                result_response = await client.post(
                    f"{base_url}/api/v1/commands/{command['id']}/result",
                    headers=command_headers,
                    json={
                        'status': result_status,
                        'result': result_payload,
                        'config_snapshot': self.config_service.get_public_config(),
                        'status_snapshot': self.build_status_snapshot(),
                    },
                )
                result_response.raise_for_status()

    async def _execute_command(self, command: dict[str, object]) -> tuple[str, dict[str, object]]:
        command_id = str(command.get('id', ''))
        command_type = str(command.get('command_type', ''))
        payload = command.get('payload') or {}
        self.config_service.record_state('last_command_origin', 'receiver-api')

        try:
            if command_type == 'update_config':
                self.config_service.update_public_config(dict(payload))
                self.command_log_repository.create(
                    command_id=command_id,
                    command_type=command_type,
                    origin='receiver-api',
                    status='success',
                    detail={
                        'payload': payload,
                        'correlation_id': get_correlation_id(),
                    },
                )
                self.db.commit()
                return 'completed', {'updated': True}

            if command_type == 'force_sync':
                result = self.perform_sync_cycle(reason='remote_command')
                return 'completed', result

            self.command_log_repository.create(
                command_id=command_id,
                command_type=command_type,
                origin='receiver-api',
                status='failure',
                detail={'error': 'unsupported_command', 'correlation_id': get_correlation_id()},
            )
            self.db.commit()
            return 'failed', {'error': 'unsupported_command'}
        except Exception as exc:  # pragma: no cover
            self.command_log_repository.create(
                command_id=command_id,
                command_type=command_type,
                origin='receiver-api',
                status='failure',
                detail={'error': str(exc), 'correlation_id': get_correlation_id()},
            )
            self.db.commit()
            return 'failed', {'error': str(exc)}

    def _remote_headers(self, *, action: str) -> dict[str, str] | None:
        token = self.config_service.current_control_token()
        if not token:
            return None
        return {
            'X-Empresa-Id': settings.control_empresa_id,
            'X-Client-Token': token,
            'X-Client-Id': self.config_service.installation_id(),
            'X-Correlation-Id': self._next_correlation_id(action),
        }

    @staticmethod
    async def background_loop(session_factory, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            with session_factory() as db:
                service = RemoteAgentService(db)
                await service.run_remote_cycle()

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=settings.remote_command_pull_interval_seconds)
            except asyncio.TimeoutError:
                continue

    @staticmethod
    def _read_tenant_api_key() -> str | None:
        file_path = Path(settings.agent_api_key_file)
        if not file_path.exists():
            return None
        token = file_path.read_text(encoding='utf-8').strip()
        return token or None

    def _next_correlation_id(self, action: str) -> str:
        base = get_correlation_id()
        if base:
            return f'{base}:{action}'
        return f'{self.config_service.installation_id()}:{action}:{uuid4().hex[:12]}'

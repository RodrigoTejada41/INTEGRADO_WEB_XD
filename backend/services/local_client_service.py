from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from backend.config.settings import get_settings
from backend.models.local_client import LocalClient
from backend.repositories.local_client_command_repository import LocalClientCommandRepository
from backend.repositories.local_client_log_repository import LocalClientLogRepository
from backend.repositories.local_client_repository import LocalClientRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.utils.security import hash_api_key, verify_api_key

settings = get_settings()


class LocalClientService:
    def __init__(
        self,
        client_repository: LocalClientRepository,
        command_repository: LocalClientCommandRepository,
        log_repository: LocalClientLogRepository,
        tenant_repository: TenantRepository,
    ):
        self.client_repository = client_repository
        self.command_repository = command_repository
        self.log_repository = log_repository
        self.tenant_repository = tenant_repository

    def register_client(
        self,
        *,
        empresa_id: str,
        client_id: str,
        hostname: str,
        ip_address: str | None,
        endpoint_url: str | None,
        raw_token: str,
        token_expires_at: datetime | None,
        config_snapshot: dict[str, object] | None,
        status_snapshot: dict[str, object] | None,
    ) -> LocalClient:
        expires_at = token_expires_at or (
            datetime.now(UTC) + timedelta(days=settings.local_client_token_expiration_days)
        )
        client = self.client_repository.upsert_registration(
            client_id=client_id,
            empresa_id=empresa_id,
            hostname=hostname,
            ip_address=ip_address,
            endpoint_url=endpoint_url,
            token_hash=hash_api_key(raw_token),
            token_last_rotated_at=datetime.now(UTC),
            token_expires_at=expires_at,
            config_snapshot=config_snapshot,
            status_snapshot=status_snapshot,
            metadata={"registered_via": "tenant_auth"},
        )
        self.log_repository.create(
            client_id=client.id,
            empresa_id=empresa_id,
            direction="inbound",
            event_type="client.register",
            origin="local_client",
            status="success",
            message="Local client registered or refreshed.",
            detail={"hostname": hostname, "endpoint_url": endpoint_url or ""},
        )
        return client

    def authenticate_client(self, *, client_id: str, empresa_id: str, raw_token: str) -> LocalClient:
        client = self.client_repository.get_by_id(client_id)
        if client is None or client.empresa_id != empresa_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Local client credentials are invalid.",
            )
        if not verify_api_key(raw_token, client.token_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Local client credentials are invalid.",
            )
        if client.token_expires_at is not None:
            expires_at = client.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Local client token expired.",
                )
        return client

    def heartbeat(
        self,
        client: LocalClient,
        *,
        config_snapshot: dict[str, object],
        status_snapshot: dict[str, object],
    ) -> LocalClient:
        updated = self.client_repository.touch_client(
            client,
            config_snapshot=config_snapshot,
            status_snapshot=status_snapshot,
            status="online",
        )
        self.log_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            direction="inbound",
            event_type="client.heartbeat",
            origin="local_client",
            status="success",
            detail={"last_sync_at": str(status_snapshot.get("last_sync_at", ""))},
        )
        return updated

    def pull_commands(self, client: LocalClient) -> list:
        commands = self.command_repository.list_pending_for_client(client.id)
        if commands:
            self.command_repository.mark_delivered(commands)
        self.client_repository.touch_client(client, command_polled=True, status="online")
        self.log_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            direction="outbound",
            event_type="commands.pull",
            origin="local_client",
            status="success",
            detail={"commands_count": len(commands)},
        )
        return commands

    def record_command_result(
        self,
        client: LocalClient,
        *,
        command_id: str,
        execution_status: str,
        result: dict[str, object],
        config_snapshot: dict[str, object],
        status_snapshot: dict[str, object],
    ):
        command = self.command_repository.get_by_id(command_id)
        if command is None or command.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Command not found for local client.",
            )
        self.command_repository.mark_result(command, status=execution_status, result=result)
        self.client_repository.touch_client(
            client,
            config_snapshot=config_snapshot,
            status_snapshot=status_snapshot,
            status="online" if execution_status == "completed" else "error",
        )
        self.log_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            direction="inbound",
            event_type=f"command.{command.command_type}",
            origin="local_client",
            status="success" if execution_status == "completed" else "failure",
            detail={
                "command_id": command.id,
                "result": result,
            },
        )
        return command

    def list_clients(
        self,
        *,
        empresa_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[LocalClient]:
        return self.client_repository.list_all(
            empresa_id=empresa_id,
            status=status,
            search=search,
        )

    def summarize_clients(
        self,
        *,
        empresa_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> dict[str, int]:
        clients = self.list_clients(empresa_id=empresa_id, status=status, search=search)
        return {
            "total_clients": len(clients),
            "online_clients": sum(1 for client in clients if client.status == "online"),
            "error_clients": sum(1 for client in clients if client.status == "error"),
            "unique_empresas": len({client.empresa_id for client in clients}),
        }

    def get_client(self, client_id: str) -> LocalClient:
        client = self.client_repository.get_by_id(client_id)
        if client is None:
            raise HTTPException(status_code=404, detail="Local client not found.")
        return client

    def enqueue_config_update(self, client_id: str, payload: dict[str, object], requested_by: str):
        client = self.get_client(client_id)
        command = self.command_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            command_type="update_config",
            payload=payload,
            requested_by=requested_by,
        )
        self.log_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            direction="outbound",
            event_type="command.update_config",
            origin="receiver_api",
            status="success",
            detail={"command_id": command.id, "payload": payload},
        )
        return client, command

    def enqueue_force_sync(self, client_id: str, requested_by: str):
        client = self.get_client(client_id)
        command = self.command_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            command_type="force_sync",
            payload={},
            requested_by=requested_by,
        )
        self.log_repository.create(
            client_id=client.id,
            empresa_id=client.empresa_id,
            direction="outbound",
            event_type="command.force_sync",
            origin="receiver_api",
            status="success",
            detail={"command_id": command.id},
        )
        return client, command

    def list_logs(self, client_id: str, limit: int = 20):
        client = self.get_client(client_id)
        return self.log_repository.list_recent(client.id, limit=limit)

    def get_empresa_nome(self, empresa_id: str) -> str | None:
        tenant = self.tenant_repository.get_by_empresa_id(empresa_id)
        if tenant is None:
            return None
        return tenant.nome

    @staticmethod
    def parse_snapshot(raw_json: str) -> dict[str, object]:
        try:
            return json.loads(raw_json or "{}")
        except json.JSONDecodeError:
            return {}

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.local_client import LocalClient


class LocalClientRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, client_id: str) -> LocalClient | None:
        return self.session.get(LocalClient, client_id)

    def get_by_empresa_and_hostname(self, empresa_id: str, hostname: str) -> LocalClient | None:
        stmt = select(LocalClient).where(
            LocalClient.empresa_id == empresa_id,
            LocalClient.hostname == hostname,
        )
        return self.session.scalar(stmt)

    def list_all(
        self,
        *,
        empresa_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[LocalClient]:
        stmt = select(LocalClient)
        if empresa_id:
            stmt = stmt.where(LocalClient.empresa_id == empresa_id)
        if status:
            stmt = stmt.where(LocalClient.status == status)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                LocalClient.hostname.ilike(like)
                | LocalClient.id.ilike(like)
                | LocalClient.empresa_id.ilike(like)
            )
        stmt = stmt.order_by(LocalClient.updated_at.desc())
        return list(self.session.scalars(stmt).all())

    def upsert_registration(
        self,
        *,
        client_id: str,
        empresa_id: str,
        hostname: str,
        ip_address: str | None,
        endpoint_url: str | None,
        token_hash: str,
        token_last_rotated_at: datetime | None,
        token_expires_at: datetime | None,
        config_snapshot: dict[str, object] | None,
        status_snapshot: dict[str, object] | None,
        metadata: dict[str, object] | None,
    ) -> LocalClient:
        entity = self.get_by_id(client_id)
        if entity is None:
            entity = LocalClient(
                id=client_id,
                empresa_id=empresa_id,
                hostname=hostname,
                ip_address=ip_address,
                endpoint_url=endpoint_url,
                token_hash=token_hash,
                token_last_rotated_at=token_last_rotated_at,
                token_expires_at=token_expires_at,
                last_config_json=json.dumps(config_snapshot or {}, ensure_ascii=False, sort_keys=True),
                last_status_json=json.dumps(status_snapshot or {}, ensure_ascii=False, sort_keys=True),
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True),
                status="online",
                last_seen_at=datetime.now(UTC),
            )
            self.session.add(entity)
            self.session.flush()
            return entity

        entity.empresa_id = empresa_id
        entity.hostname = hostname
        entity.ip_address = ip_address
        entity.endpoint_url = endpoint_url
        entity.token_hash = token_hash
        entity.token_last_rotated_at = token_last_rotated_at
        entity.token_expires_at = token_expires_at
        entity.status = "online"
        entity.last_seen_at = datetime.now(UTC)
        entity.last_config_json = json.dumps(config_snapshot or {}, ensure_ascii=False, sort_keys=True)
        entity.last_status_json = json.dumps(status_snapshot or {}, ensure_ascii=False, sort_keys=True)
        entity.metadata_json = json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        entity.last_sync_at = self._parse_datetime((status_snapshot or {}).get("last_sync_at"))
        self.session.flush()
        return entity

    def touch_client(
        self,
        client: LocalClient,
        *,
        config_snapshot: dict[str, object] | None = None,
        status_snapshot: dict[str, object] | None = None,
        command_polled: bool = False,
        status: str | None = None,
    ) -> LocalClient:
        now = datetime.now(UTC)
        client.last_seen_at = now
        if command_polled:
            client.last_command_poll_at = now
        if config_snapshot is not None:
            client.last_config_json = json.dumps(config_snapshot, ensure_ascii=False, sort_keys=True)
        if status_snapshot is not None:
            client.last_status_json = json.dumps(status_snapshot, ensure_ascii=False, sort_keys=True)
            client.last_sync_at = self._parse_datetime(status_snapshot.get("last_sync_at"))
        if status:
            client.status = status
        self.session.flush()
        return client

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

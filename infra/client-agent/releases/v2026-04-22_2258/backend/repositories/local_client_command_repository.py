from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.local_client_command import LocalClientCommand


class LocalClientCommandRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        client_id: str,
        empresa_id: str,
        command_type: str,
        payload: dict[str, object] | None,
        requested_by: str,
        origin: str = "web",
    ) -> LocalClientCommand:
        entity = LocalClientCommand(
            id=str(uuid4()),
            client_id=client_id,
            empresa_id=empresa_id,
            command_type=command_type,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
            requested_by=requested_by,
            origin=origin,
            status="pending",
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def get_by_id(self, command_id: str) -> LocalClientCommand | None:
        return self.session.get(LocalClientCommand, command_id)

    def list_pending_for_client(self, client_id: str) -> list[LocalClientCommand]:
        stmt = (
            select(LocalClientCommand)
            .where(
                LocalClientCommand.client_id == client_id,
                LocalClientCommand.status == "pending",
            )
            .order_by(LocalClientCommand.created_at.asc())
        )
        return list(self.session.scalars(stmt).all())

    def mark_delivered(self, commands: list[LocalClientCommand]) -> None:
        delivered_at = datetime.now(UTC)
        for command in commands:
            command.status = "delivered"
            command.delivered_at = delivered_at
        self.session.flush()

    def mark_result(
        self,
        command: LocalClientCommand,
        *,
        status: str,
        result: dict[str, object] | None,
    ) -> LocalClientCommand:
        command.status = status
        command.result_json = json.dumps(result or {}, ensure_ascii=False, sort_keys=True)
        command.executed_at = datetime.now(UTC)
        self.session.flush()
        return command

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session


class TenantConfigRepository:
    def __init__(self, session: Session, model: type[Any]):
        self.session = session
        self.model = model

    def create(
        self,
        *,
        config_id: str,
        empresa_id: str,
        nome: str,
        connector_type: str,
        sync_interval_minutes: int,
        settings_json: str,
        ativo: bool = True,
    ) -> Any:
        item = self.model(
            id=config_id,
            empresa_id=empresa_id,
            nome=nome,
            connector_type=connector_type,
            sync_interval_minutes=sync_interval_minutes,
            settings_json=settings_json,
            ativo=ativo,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def list_by_empresa_id(self, empresa_id: str) -> list[Any]:
        stmt = select(self.model).where(self.model.empresa_id == empresa_id).order_by(self.model.created_at)
        return list(self.session.scalars(stmt).all())

    def get_by_id(self, empresa_id: str, config_id: str) -> Any | None:
        stmt = select(self.model).where(
            self.model.empresa_id == empresa_id,
            self.model.id == config_id,
        )
        return self.session.scalar(stmt)

    def update(self, item: Any, **fields: Any) -> Any:
        for key, value in fields.items():
            if value is not None:
                setattr(item, key, value)
        self.session.flush()
        return item

    def delete(self, item: Any) -> None:
        self.session.delete(item)
        self.session.flush()

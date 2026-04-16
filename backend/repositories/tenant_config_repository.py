from __future__ import annotations

from typing import Any

from sqlalchemy import case, func, select
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

    def list_active_by_empresa_id(self, empresa_id: str) -> list[Any]:
        stmt = (
            select(self.model)
            .where(self.model.empresa_id == empresa_id, self.model.ativo.is_(True))
            .order_by(self.model.created_at)
        )
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

    def summary_by_empresa_id(self, empresa_id: str) -> dict[str, Any]:
        stmt = select(
            func.count(self.model.id),
            func.sum(case((self.model.ativo.is_(True), 1), else_=0)),
            func.sum(case((self.model.ativo.is_(False), 1), else_=0)),
            func.sum(case((self.model.last_status == "pending", 1), else_=0)),
            func.sum(case((self.model.last_status == "ok", 1), else_=0)),
            func.sum(case((self.model.last_status == "failed", 1), else_=0)),
            func.sum(case((self.model.last_status == "retrying", 1), else_=0)),
            func.sum(case((self.model.last_status == "dead_letter", 1), else_=0)),
        ).where(self.model.empresa_id == empresa_id)
        row = self.session.execute(stmt).one()
        connector_stmt = (
            select(self.model.connector_type)
            .where(self.model.empresa_id == empresa_id)
            .distinct()
            .order_by(self.model.connector_type)
        )
        connector_types = list(self.session.scalars(connector_stmt).all())
        return {
            "total_count": int(row[0] or 0),
            "active_count": int(row[1] or 0),
            "inactive_count": int(row[2] or 0),
            "pending_count": int(row[3] or 0),
            "ok_count": int(row[4] or 0),
            "failed_count": int(row[5] or 0),
            "retrying_count": int(row[6] or 0),
            "dead_letter_count": int(row[7] or 0),
            "connector_types": connector_types,
        }

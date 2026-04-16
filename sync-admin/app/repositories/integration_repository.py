from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.integration_key import IntegrationKey


class IntegrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_hash(self, key_hash: str) -> IntegrationKey | None:
        stmt = select(IntegrationKey).where(IntegrationKey.key_hash == key_hash, IntegrationKey.is_active.is_(True))
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, key_hash: str, key_prefix: str, description: str = 'Default sync integration key') -> IntegrationKey:
        entity = IntegrationKey(key_hash=key_hash, key_prefix=key_prefix, description=description)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def touch_used(self, entity: IntegrationKey) -> None:
        entity.last_used_at = datetime.now(timezone.utc)
        self.db.add(entity)
        self.db.commit()

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.local_runtime_setting import LocalRuntimeSetting


class LocalRuntimeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> LocalRuntimeSetting | None:
        return self.db.get(LocalRuntimeSetting, key)

    def get_value(self, key: str, default: Any = None) -> Any:
        entity = self.get(key)
        if entity is None:
            return default
        return json.loads(entity.value_json)

    def set_value(self, key: str, value: Any) -> LocalRuntimeSetting:
        entity = self.get(key)
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if entity is None:
            entity = LocalRuntimeSetting(
                key=key,
                value_json=encoded,
                updated_at=datetime.now(timezone.utc),
            )
            self.db.add(entity)
        else:
            entity.value_json = encoded
            entity.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        return entity

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.server_setting import ServerSetting


class ServerSettingRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_many(self, keys: list[str]) -> dict[str, str]:
        if not keys:
            return {}
        stmt = select(ServerSetting).where(ServerSetting.key.in_(keys))
        rows = self.session.scalars(stmt).all()
        return {row.key: row.value for row in rows}

    def get_all(self) -> dict[str, str]:
        stmt = select(ServerSetting)
        rows = self.session.scalars(stmt).all()
        return {row.key: row.value for row in rows}

    def upsert(self, key: str, value: str) -> None:
        item = self.session.get(ServerSetting, key)
        if item is None:
            item = ServerSetting(key=key, value=value)
            self.session.add(item)
            self.session.flush()
            return
        item.value = value
        self.session.flush()


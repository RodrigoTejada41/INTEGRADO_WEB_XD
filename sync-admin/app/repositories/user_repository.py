from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

_UNSET = object()


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def list_all(self) -> list[User]:
        stmt = select(User).order_by(User.role.asc(), User.username.asc())
        return list(self.db.scalars(stmt).all())

    def create(
        self,
        username: str,
        full_name: str,
        password_hash: str,
        role: str = 'admin',
        empresa_id: str | None = None,
        scope_type: str | None = None,
    ) -> User:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            empresa_id=empresa_id,
            scope_type=scope_type,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_fields(
        self,
        user_id: int,
        *,
        full_name: str | None | object = _UNSET,
        role: str | None | object = _UNSET,
        empresa_id: str | None | object = _UNSET,
        scope_type: str | None | object = _UNSET,
        is_active: bool | None | object = _UNSET,
        password_hash: str | None | object = _UNSET,
    ) -> User | None:
        user = self.by_id(user_id)
        if not user:
            return None
        if full_name is not _UNSET:
            user.full_name = full_name
        if role is not _UNSET:
            user.role = role
        if empresa_id is not _UNSET:
            user.empresa_id = empresa_id
        if scope_type is not _UNSET:
            user.scope_type = scope_type
        if is_active is not _UNSET:
            user.is_active = is_active
        if password_hash is not _UNSET:
            user.password_hash = password_hash
        self.db.flush()
        return user

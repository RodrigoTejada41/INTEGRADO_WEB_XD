from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


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

    def create(self, username: str, full_name: str, password_hash: str, role: str = 'admin') -> User:
        user = User(username=username, full_name=full_name, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_fields(
        self,
        user_id: int,
        *,
        full_name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        password_hash: str | None = None,
    ) -> User | None:
        user = self.by_id(user_id)
        if not user:
            return None
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if is_active is not None:
            user.is_active = is_active
        if password_hash is not None:
            user.password_hash = password_hash
        self.db.flush()
        return user

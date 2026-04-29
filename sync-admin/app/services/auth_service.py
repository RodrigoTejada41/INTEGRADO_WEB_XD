from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.db = db

    def ensure_initial_admin(self, username: str, password: str) -> None:
        exists = self.repo.by_username(username)
        if exists:
            return
        self.repo.create(username=username, full_name='Administrator', password_hash=hash_password(password), role='admin')

    def ensure_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role: str,
        empresa_id: str | None = None,
        scope_type: str | None = None,
    ) -> None:
        exists = self.repo.by_username(username)
        if exists:
            return
        self.repo.create(
            username=username,
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
            empresa_id=empresa_id,
            scope_type=scope_type,
        )

    def ensure_initial_client(
        self,
        *,
        username: str,
        full_name: str,
        password: str,
        empresa_id: str,
    ) -> None:
        self.ensure_user(
            username=username,
            full_name=full_name,
            password=password,
            role='client',
            empresa_id=empresa_id,
            scope_type='company',
        )

    def login(self, username: str, password: str) -> User | None:
        user = self.repo.by_username(username)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None

        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()
        return user

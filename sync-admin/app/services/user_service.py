from __future__ import annotations

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.schemas.users import UserCreateRequest, UserResponse


class UserService:
    ALLOWED_ROLES = {"admin", "analyst", "viewer"}

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def list_users(self) -> list[UserResponse]:
        return [UserResponse.model_validate(user) for user in self.repository.list_all()]

    def create_user(self, payload: UserCreateRequest) -> UserResponse:
        if payload.role not in self.ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role invalida.")
        if self.repository.by_username(payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe.")

        user = self.repository.create(
            username=payload.username,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        return UserResponse.model_validate(user)

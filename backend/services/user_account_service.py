import uuid

from fastapi import HTTPException, status

from backend.models.user_account import UserAccount
from backend.repositories.empresa_repository import EmpresaRepository
from backend.repositories.user_account_repository import UserAccountRepository
from backend.schemas.user_account import UserCreateRequest, UserUpdateRequest
from backend.utils.security import hash_password


class UserAccountService:
    def __init__(self, user_repository: UserAccountRepository, empresa_repository: EmpresaRepository) -> None:
        self.user_repository = user_repository
        self.empresa_repository = empresa_repository

    def list_users(self, empresa_id: str | None = None) -> list[UserAccount]:
        if empresa_id:
            return self.user_repository.list_by_empresa(empresa_id)
        return self.user_repository.list_all()

    def get_user(self, user_id: str) -> UserAccount:
        user = self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def create_user(self, payload: UserCreateRequest, default_empresa_id: str | None = None) -> UserAccount:
        empresa_id = payload.empresa_id or default_empresa_id
        if not empresa_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empresa_id required")
        if not self.empresa_repository.get_by_id(empresa_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa not found")
        if self.user_repository.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
        user = UserAccount(
            id=str(uuid.uuid4()),
            empresa_id=empresa_id,
            nome=payload.nome.strip(),
            email=payload.email.lower(),
            role=payload.role,
            password_hash=hash_password(payload.password),
        )
        return self.user_repository.add(user)

    def update_user(self, user_id: str, payload: UserUpdateRequest) -> UserAccount:
        user = self.get_user(user_id)
        if payload.nome is not None:
            user.nome = payload.nome.strip()
        if payload.role is not None:
            user.role = payload.role
        if payload.ativo is not None:
            user.ativo = payload.ativo
        return user

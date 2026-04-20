import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from backend.config.settings import get_settings
from backend.models.refresh_token import RefreshToken
from backend.models.user_account import UserAccount
from backend.repositories.empresa_repository import EmpresaRepository
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_account_repository import UserAccountRepository
from backend.schemas.auth import TokenPairResponse
from backend.utils.security import create_jwt_token, decode_jwt_token, verify_password


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(
        self,
        user_repository: UserAccountRepository,
        empresa_repository: EmpresaRepository,
        refresh_repository: RefreshTokenRepository,
    ) -> None:
        self.user_repository = user_repository
        self.empresa_repository = empresa_repository
        self.refresh_repository = refresh_repository
        self.settings = get_settings()

    def authenticate(self, email: str, password: str) -> UserAccount:
        user = self.user_repository.get_by_email(email.lower())
        if not user or not user.ativo:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return user

    def issue_tokens(self, user: UserAccount) -> TokenPairResponse:
        empresa = self.empresa_repository.get_by_id(user.empresa_id)
        if not empresa or not empresa.ativo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inactive")
        claims = {"empresa_id": user.empresa_id, "empresa_cnpj": empresa.cnpj, "role": user.role, "email": user.email}
        access_expires = timedelta(minutes=self.settings.jwt_access_expires_minutes)
        refresh_expires = timedelta(minutes=self.settings.jwt_refresh_expires_minutes)
        access_token = create_jwt_token(user.id, "access", access_expires, claims)
        refresh_token = create_jwt_token(user.id, "refresh", refresh_expires, claims)
        self.refresh_repository.add(
            RefreshToken(
                id=str(uuid.uuid4()),
                user_id=user.id,
                token_hash=_hash_refresh_token(refresh_token),
                expires_at=datetime.now(UTC) + refresh_expires,
                revoked=False,
            )
        )
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.jwt_access_expires_minutes * 60,
        )

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = decode_jwt_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        token_hash = _hash_refresh_token(refresh_token)
        token_record = self.refresh_repository.get_by_hash(token_hash)
        if not token_record or token_record.revoked or token_record.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid")
        user = self.user_repository.get_by_id(payload["sub"])
        if not user or not user.ativo:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
        token_record.revoked = True
        return self.issue_tokens(user)

    def logout(self, user_id: str, refresh_token: str | None) -> None:
        if refresh_token:
            token_hash = _hash_refresh_token(refresh_token)
            token_record = self.refresh_repository.get_by_hash(token_hash)
            if token_record:
                token_record.revoked = True
                return
        self.refresh_repository.revoke_by_user(user_id)

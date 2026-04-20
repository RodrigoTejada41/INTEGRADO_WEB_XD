from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.config.database import get_session
from backend.repositories.user_account_repository import UserAccountRepository
from backend.utils.security import decode_jwt_token


@dataclass
class AuthContext:
    user_id: str
    empresa_id: str
    empresa_cnpj: str
    role: str
    email: str


def get_auth_context(authorization: str = Header(default="")) -> AuthContext:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_jwt_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return AuthContext(
        user_id=payload["sub"],
        empresa_id=payload.get("empresa_id", ""),
        empresa_cnpj=payload.get("empresa_cnpj", ""),
        role=payload.get("role", "viewer"),
        email=payload.get("email", ""),
    )


def require_authenticated_user(
    auth: AuthContext = Depends(get_auth_context),
    session: Session = Depends(get_session),
) -> AuthContext:
    user = UserAccountRepository(session).get_by_id(auth.user_id)
    if not user or not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return auth


def require_admin_or_manager(auth: AuthContext = Depends(require_authenticated_user)) -> AuthContext:
    if auth.role not in {"superadmin", "admin", "manager"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return auth


def require_superadmin(auth: AuthContext = Depends(require_authenticated_user)) -> AuthContext:
    if auth.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    return auth

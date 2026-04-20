from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.auth_deps import AuthContext, require_authenticated_user
from backend.config.database import get_session
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.empresa_repository import EmpresaRepository
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_account_repository import UserAccountRepository
from backend.schemas.auth import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenPairResponse
from backend.services.audit_log_service import AuditLogService
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _auth_service(session: Session) -> AuthService:
    return AuthService(
        UserAccountRepository(session),
        EmpresaRepository(session),
        RefreshTokenRepository(session),
    )


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenPairResponse:
    service = _auth_service(session)
    user = service.authenticate(payload.email, payload.password)
    tokens = service.issue_tokens(user)
    AuditLogService(AuditLogRepository(session)).log(user.empresa_id, user.id, "auth.login", "auth", {"email": user.email})
    session.commit()
    return tokens


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> TokenPairResponse:
    tokens = _auth_service(session).refresh(payload.refresh_token)
    session.commit()
    return tokens


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    auth: AuthContext = Depends(require_authenticated_user),
    session: Session = Depends(get_session),
) -> dict:
    _auth_service(session).logout(auth.user_id, payload.refresh_token)
    AuditLogService(AuditLogRepository(session)).log(auth.empresa_id, auth.user_id, "auth.logout", "auth", {})
    session.commit()
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(
    auth: AuthContext = Depends(require_authenticated_user),
    session: Session = Depends(get_session),
) -> MeResponse:
    user = UserAccountRepository(session).get_by_id(auth.user_id)
    return MeResponse(
        user_id=auth.user_id,
        empresa_id=auth.empresa_id,
        empresa_cnpj=auth.empresa_cnpj,
        nome=user.nome if user else "",
        email=auth.email,
        role=auth.role,
    )

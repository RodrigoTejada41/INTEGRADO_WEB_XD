from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.auth_deps import AuthContext, require_admin_or_manager
from backend.config.database import get_session
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.empresa_repository import EmpresaRepository
from backend.repositories.user_account_repository import UserAccountRepository
from backend.schemas.user_account import UserCreateRequest, UserResponse, UserUpdateRequest
from backend.services.audit_log_service import AuditLogService
from backend.services.user_account_service import UserAccountService

router = APIRouter(prefix="/api/v1/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UserResponse])
def list_users(
    auth: AuthContext = Depends(require_admin_or_manager),
    session: Session = Depends(get_session),
) -> list[UserResponse]:
    service = UserAccountService(UserAccountRepository(session), EmpresaRepository(session))
    users = service.list_users(None if auth.role == "superadmin" else auth.empresa_id)
    return [UserResponse(**_to_user_payload(user)) for user in users]


@router.post("", response_model=UserResponse)
def create_user(
    payload: UserCreateRequest,
    auth: AuthContext = Depends(require_admin_or_manager),
    session: Session = Depends(get_session),
) -> UserResponse:
    if auth.role != "superadmin" and payload.empresa_id and payload.empresa_id != auth.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant isolation violation")
    service = UserAccountService(UserAccountRepository(session), EmpresaRepository(session))
    user = service.create_user(payload, default_empresa_id=auth.empresa_id if auth.role != "superadmin" else None)
    AuditLogService(AuditLogRepository(session)).log(auth.empresa_id, auth.user_id, "user.create", "user", {"user_id": user.id})
    session.commit()
    return UserResponse(**_to_user_payload(user))


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    auth: AuthContext = Depends(require_admin_or_manager),
    session: Session = Depends(get_session),
) -> UserResponse:
    service = UserAccountService(UserAccountRepository(session), EmpresaRepository(session))
    existing = service.get_user(user_id)
    if auth.role != "superadmin" and existing.empresa_id != auth.empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant isolation violation")
    user = service.update_user(user_id, payload)
    AuditLogService(AuditLogRepository(session)).log(auth.empresa_id, auth.user_id, "user.update", "user", {"user_id": user.id})
    session.commit()
    return UserResponse(**_to_user_payload(user))


def _to_user_payload(user) -> dict:
    return {
        "id": user.id,
        "empresa_id": user.empresa_id,
        "nome": user.nome,
        "email": user.email,
        "role": user.role,
        "ativo": user.ativo,
    }

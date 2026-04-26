from __future__ import annotations

from fastapi import HTTPException, status

from app.core.security import hash_password
from app.repositories.admin_user_audit_log_repository import AdminUserAuditLogRepository
from app.repositories.user_branch_permission_repository import UserBranchPermissionRepository
from app.repositories.user_repository import UserRepository, _UNSET
from app.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest


class UserService:
    ALLOWED_ROLES = {"admin", "analyst", "viewer", "client"}
    CLIENT_SCOPE_TYPES = {"company", "branch_set"}

    def __init__(
        self,
        repository: UserRepository,
        branch_repository: UserBranchPermissionRepository | None = None,
        audit_repository: AdminUserAuditLogRepository | None = None,
    ):
        self.repository = repository
        self.branch_repository = branch_repository or UserBranchPermissionRepository(repository.db)
        self.audit_repository = audit_repository or AdminUserAuditLogRepository(repository.db)

    def list_users(self) -> list[UserResponse]:
        return [self._to_response(user) for user in self.repository.list_all()]

    def _validate_client_scope(
        self,
        *,
        role: str,
        empresa_id: str | None,
        scope_type: str | None,
        allowed_branch_codes: list[str],
    ) -> None:
        if role not in self.ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role invalida.")
        if role != "client":
            return
        if not empresa_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empresa_id obrigatorio para client.")
        if scope_type not in self.CLIENT_SCOPE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope_type obrigatorio para client.")
        if scope_type == "branch_set" and not allowed_branch_codes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filiais obrigatorias para branch_set.")

    def create_user(self, payload: UserCreateRequest) -> UserResponse:
        self._validate_client_scope(
            role=payload.role,
            empresa_id=payload.empresa_id,
            scope_type=payload.scope_type,
            allowed_branch_codes=payload.allowed_branch_codes,
        )
        if self.repository.by_username(payload.username):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuario ja existe.")

        user = self.repository.create(
            username=payload.username,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            empresa_id=payload.empresa_id,
            scope_type=payload.scope_type if payload.role == "client" else None,
        )
        if payload.role == "client" and payload.scope_type == "branch_set":
            self.branch_repository.replace_permissions(
                user_id=user.id,
                empresa_id=str(payload.empresa_id),
                branch_codes=payload.allowed_branch_codes,
            )
            self.repository.db.commit()
            self.repository.db.refresh(user)
        return self._to_response(user)

    def create_user_with_audit(
        self,
        payload: UserCreateRequest,
        *,
        actor: str,
        audit_context: dict[str, str] | None = None,
    ) -> UserResponse:
        created = self.create_user(payload)
        self.audit_repository.create(
            actor=actor,
            action="user.create",
            resource_id=str(created.id),
            target_username=created.username,
            detail={
                "after": {
                    "role": created.role,
                    "empresa_id": created.empresa_id,
                    "scope_type": created.scope_type,
                    "allowed_branch_codes": created.allowed_branch_codes,
                    "is_active": created.is_active,
                }
            },
            correlation_id=(audit_context or {}).get("correlation_id"),
            request_path=(audit_context or {}).get("request_path"),
            actor_ip=(audit_context or {}).get("actor_ip"),
            user_agent=(audit_context or {}).get("user_agent"),
        )
        self.repository.db.commit()
        return created

    def update_user(self, user_id: int, payload: UserUpdateRequest) -> UserResponse:
        self._validate_client_scope(
            role=payload.role,
            empresa_id=payload.empresa_id,
            scope_type=payload.scope_type,
            allowed_branch_codes=payload.allowed_branch_codes,
        )
        current = self.repository.by_id(user_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")

        before_allowed_branch_codes = self.branch_repository.list_branch_codes(user_id=user_id)
        before_snapshot = {
            "full_name": current.full_name,
            "role": current.role,
            "empresa_id": current.empresa_id,
            "scope_type": current.scope_type,
            "allowed_branch_codes": before_allowed_branch_codes,
            "is_active": current.is_active,
        }
        user = self.repository.update_fields(
            user_id,
            full_name=payload.full_name,
            role=payload.role,
            empresa_id=payload.empresa_id if payload.role == "client" else None,
            scope_type=payload.scope_type if payload.role == "client" else None,
            is_active=payload.is_active,
            password_hash=hash_password(payload.password) if payload.password else _UNSET,
        )
        if payload.role == "client" and payload.scope_type == "branch_set":
            self.branch_repository.replace_permissions(
                user_id=user.id,
                empresa_id=str(payload.empresa_id),
                branch_codes=payload.allowed_branch_codes,
            )
        else:
            self.branch_repository.replace_permissions(
                user_id=user.id,
                empresa_id=str(payload.empresa_id or ""),
                branch_codes=[],
            )
        self.repository.db.commit()
        self.repository.db.refresh(user)
        return self._to_response(user)

    def update_user_with_audit(
        self,
        user_id: int,
        payload: UserUpdateRequest,
        *,
        actor: str,
        audit_context: dict[str, str] | None = None,
    ) -> UserResponse:
        current = self.repository.by_id(user_id)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
        before_allowed_branch_codes = self.branch_repository.list_branch_codes(user_id=user_id)
        before_snapshot = {
            "full_name": current.full_name,
            "role": current.role,
            "empresa_id": current.empresa_id,
            "scope_type": current.scope_type,
            "allowed_branch_codes": before_allowed_branch_codes,
            "is_active": current.is_active,
        }
        updated = self.update_user(user_id, payload)
        after_snapshot = {
            "full_name": updated.full_name,
            "role": updated.role,
            "empresa_id": updated.empresa_id,
            "scope_type": updated.scope_type,
            "allowed_branch_codes": updated.allowed_branch_codes,
            "is_active": updated.is_active,
        }
        scope_changed = any(
            before_snapshot[key] != after_snapshot[key]
            for key in ("role", "empresa_id", "scope_type", "allowed_branch_codes")
        )
        self.audit_repository.create(
            actor=actor,
            action="user.scope.update" if scope_changed else "user.update",
            resource_id=str(updated.id),
            target_username=updated.username,
            detail={"before": before_snapshot, "after": after_snapshot},
            correlation_id=(audit_context or {}).get("correlation_id"),
            request_path=(audit_context or {}).get("request_path"),
            actor_ip=(audit_context or {}).get("actor_ip"),
            user_agent=(audit_context or {}).get("user_agent"),
        )
        self.repository.db.commit()
        return updated

    def _to_response(self, user) -> UserResponse:
        allowed_branch_codes: list[str] = []
        if user.role == "client" and user.scope_type == "branch_set":
            allowed_branch_codes = self.branch_repository.list_branch_codes(user_id=user.id)
        return UserResponse(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            empresa_id=user.empresa_id,
            scope_type=user.scope_type,
            allowed_branch_codes=allowed_branch_codes,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
        )

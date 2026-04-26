from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.user_branch_permission_repository import UserBranchPermissionRepository
from app.services.control_service import ControlService


@dataclass
class ClientReportScope:
    empresa_id: str
    allowed_branch_codes: list[str]
    selected_branch_code: str | None


class ClientScopeService:
    def __init__(
        self,
        control_service: ControlService,
        branch_repository: UserBranchPermissionRepository,
    ) -> None:
        self.control_service = control_service
        self.branch_repository = branch_repository

    def resolve(
        self,
        *,
        user: User,
        requested_branch_code: str | None,
        start_date: str | None = None,
        end_date: str | None = None,
        terminal_code: str | None = None,
    ) -> ClientReportScope:
        if user.role != "client" or not user.empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso restrito ao portal do cliente.",
            )

        available_branch_codes = self.control_service.fetch_report_branch_options(
            empresa_id=user.empresa_id,
            start_date=start_date,
            end_date=end_date,
            terminal_code=terminal_code,
        )
        effective_scope_type = user.scope_type or "company"
        if effective_scope_type == "company":
            allowed_branch_codes = available_branch_codes
        else:
            branch_codes = self.branch_repository.list_branch_codes(user_id=user.id)
            allowed_branch_codes = [code for code in available_branch_codes if code in branch_codes]

        if requested_branch_code and requested_branch_code not in allowed_branch_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Filial fora do escopo autorizado.",
            )

        return ClientReportScope(
            empresa_id=user.empresa_id,
            allowed_branch_codes=allowed_branch_codes,
            selected_branch_code=requested_branch_code or None,
        )

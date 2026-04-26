from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_branch_permission import UserBranchPermission


class UserBranchPermissionRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace_permissions(self, *, user_id: int, empresa_id: str, branch_codes: list[str]) -> None:
        self.db.execute(delete(UserBranchPermission).where(UserBranchPermission.user_id == user_id))
        for branch_code in sorted(set(branch_codes)):
            self.db.add(
                UserBranchPermission(
                    user_id=user_id,
                    empresa_id=empresa_id,
                    branch_code=branch_code,
                    can_view_reports=True,
                )
            )
        self.db.flush()

    def list_branch_codes(self, *, user_id: int) -> list[str]:
        stmt = (
            select(UserBranchPermission.branch_code)
            .where(
                UserBranchPermission.user_id == user_id,
                UserBranchPermission.can_view_reports.is_(True),
            )
            .order_by(UserBranchPermission.branch_code.asc())
        )
        return list(self.db.scalars(stmt).all())

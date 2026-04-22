from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.tenant_pairing_code import TenantPairingCode


class TenantPairingRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_code(
        self,
        *,
        empresa_id: str,
        code_hash: str,
        expires_at: datetime,
        created_by: str,
    ) -> TenantPairingCode:
        item = TenantPairingCode(
            id=str(uuid4()),
            empresa_id=empresa_id,
            code_hash=code_hash,
            expires_at=expires_at,
            created_by=created_by,
            active=True,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def get_active_by_hash(self, code_hash: str) -> TenantPairingCode | None:
        now = datetime.now(UTC)
        stmt = select(TenantPairingCode).where(
            TenantPairingCode.code_hash == code_hash,
            TenantPairingCode.active.is_(True),
            TenantPairingCode.used_at.is_(None),
            TenantPairingCode.expires_at >= now,
        )
        return self.session.scalar(stmt)

    def mark_used(self, item: TenantPairingCode, used_by: str) -> TenantPairingCode:
        item.used_by = used_by
        item.used_at = datetime.now(UTC)
        item.active = False
        self.session.flush()
        return item

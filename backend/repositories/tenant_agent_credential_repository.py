from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.tenant_agent_credential import TenantAgentCredential


class TenantAgentCredentialRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        *,
        empresa_id: str,
        device_label: str,
        api_key_hash: str,
    ) -> TenantAgentCredential:
        item = TenantAgentCredential(
            id=str(uuid4()),
            empresa_id=empresa_id,
            device_label=device_label,
            api_key_hash=api_key_hash,
            active=True,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def list_active_by_empresa(self, empresa_id: str) -> list[TenantAgentCredential]:
        stmt = select(TenantAgentCredential).where(
            TenantAgentCredential.empresa_id == empresa_id,
            TenantAgentCredential.active.is_(True),
        )
        return list(self.session.scalars(stmt).all())

    def mark_last_used(self, credential: TenantAgentCredential) -> None:
        credential.last_used_at = datetime.now(UTC)
        self.session.flush()

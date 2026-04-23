from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.tenant import Tenant


class TenantRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_tenant(self, empresa_id: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.empresa_id == empresa_id, Tenant.ativo.is_(True))
        return self.session.scalar(stmt)

    def get_by_empresa_id(self, empresa_id: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.empresa_id == empresa_id)
        return self.session.scalar(stmt)

    def upsert_tenant(
        self,
        empresa_id: str,
        nome: str,
        api_key_hash: str,
        api_key_last_rotated_at: datetime | None = None,
        api_key_expires_at: datetime | None = None,
    ) -> Tenant:
        tenant = self.get_by_empresa_id(empresa_id)
        if tenant is None:
            tenant = Tenant(
                empresa_id=empresa_id,
                nome=nome,
                api_key_hash=api_key_hash,
                api_key_last_rotated_at=api_key_last_rotated_at,
                api_key_expires_at=api_key_expires_at,
                ativo=True,
            )
            self.session.add(tenant)
            self.session.flush()
            return tenant

        tenant.nome = nome
        tenant.api_key_hash = api_key_hash
        tenant.api_key_last_rotated_at = api_key_last_rotated_at
        tenant.api_key_expires_at = api_key_expires_at
        tenant.ativo = True
        self.session.flush()
        return tenant

    def rotate_api_key(
        self,
        empresa_id: str,
        new_api_key_hash: str,
        api_key_last_rotated_at: datetime | None = None,
        api_key_expires_at: datetime | None = None,
    ) -> Tenant | None:
        tenant = self.get_by_empresa_id(empresa_id)
        if tenant is None:
            return None
        tenant.api_key_hash = new_api_key_hash
        tenant.api_key_last_rotated_at = api_key_last_rotated_at
        tenant.api_key_expires_at = api_key_expires_at
        self.session.flush()
        return tenant

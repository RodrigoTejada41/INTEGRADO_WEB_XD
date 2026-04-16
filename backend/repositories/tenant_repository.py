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

    def upsert_tenant(self, empresa_id: str, nome: str, api_key_hash: str) -> Tenant:
        tenant = self.get_by_empresa_id(empresa_id)
        if tenant is None:
            tenant = Tenant(
                empresa_id=empresa_id,
                nome=nome,
                api_key_hash=api_key_hash,
                ativo=True,
            )
            self.session.add(tenant)
            self.session.flush()
            return tenant

        tenant.nome = nome
        tenant.api_key_hash = api_key_hash
        tenant.ativo = True
        self.session.flush()
        return tenant

    def rotate_api_key(self, empresa_id: str, new_api_key_hash: str) -> Tenant | None:
        tenant = self.get_by_empresa_id(empresa_id)
        if tenant is None:
            return None
        tenant.api_key_hash = new_api_key_hash
        self.session.flush()
        return tenant

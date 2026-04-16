from fastapi import HTTPException, status

from backend.models.tenant import Tenant
from backend.repositories.tenant_repository import TenantRepository
from backend.utils.security import validate_empresa_id, verify_api_key


class TenantService:
    def __init__(self, repository: TenantRepository):
        self.repository = repository

    def authenticate(self, empresa_id: str, api_key: str) -> Tenant:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )

        tenant = self.repository.get_active_tenant(empresa_id)
        if tenant is None or not verify_api_key(api_key, tenant.api_key_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas.",
            )
        return tenant


from fastapi import HTTPException, status

from backend.models.tenant import Tenant
from backend.repositories.tenant_agent_credential_repository import TenantAgentCredentialRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.utils.security import validate_empresa_id, verify_api_key


class TenantService:
    def __init__(
        self,
        repository: TenantRepository,
        credential_repository: TenantAgentCredentialRepository,
    ):
        self.repository = repository
        self.credential_repository = credential_repository

    def authenticate(self, empresa_id: str, api_key: str) -> Tenant:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )

        tenant = self.repository.get_active_tenant(empresa_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais invalidas.",
            )

        if verify_api_key(api_key, tenant.api_key_hash):
            return tenant

        credentials = self.credential_repository.list_active_by_empresa(empresa_id)
        for credential in credentials:
            if verify_api_key(api_key, credential.api_key_hash):
                self.credential_repository.mark_last_used(credential)
                return tenant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas.",
        )


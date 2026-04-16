from fastapi import HTTPException, status

from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.tenant import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRotateKeyResponse,
)
from backend.utils.security import generate_api_key, hash_api_key, validate_empresa_id


class AdminService:
    def __init__(self, tenant_repository: TenantRepository):
        self.tenant_repository = tenant_repository

    def provision_tenant(self, payload: TenantProvisionRequest) -> TenantProvisionResponse:
        if not validate_empresa_id(payload.empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )
        raw_api_key = generate_api_key()
        api_key_hash = hash_api_key(raw_api_key)
        tenant = self.tenant_repository.upsert_tenant(
            empresa_id=payload.empresa_id,
            nome=payload.nome,
            api_key_hash=api_key_hash,
        )
        return TenantProvisionResponse(
            empresa_id=tenant.empresa_id,
            nome=tenant.nome,
            api_key=raw_api_key,
            status="ok",
        )

    def rotate_tenant_key(self, empresa_id: str) -> TenantRotateKeyResponse:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )
        raw_api_key = generate_api_key()
        api_key_hash = hash_api_key(raw_api_key)
        tenant = self.tenant_repository.rotate_api_key(
            empresa_id=empresa_id,
            new_api_key_hash=api_key_hash,
        )
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant nao encontrado.",
            )
        return TenantRotateKeyResponse(
            empresa_id=tenant.empresa_id,
            api_key=raw_api_key,
            status="ok",
        )


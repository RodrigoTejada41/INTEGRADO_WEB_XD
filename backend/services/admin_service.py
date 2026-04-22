from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from backend.config.settings import get_settings
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.tenant import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRotateKeyResponse,
)
from backend.utils.security import generate_api_key, hash_api_key, validate_empresa_id

settings = get_settings()


class AdminService:
    def __init__(self, tenant_repository: TenantRepository):
        self.tenant_repository = tenant_repository

    @staticmethod
    def _build_api_key_lifecycle() -> tuple[datetime, datetime | None]:
        rotated_at = datetime.now(UTC)
        if settings.tenant_api_key_expiration_days <= 0:
            return rotated_at, None
        expires_at = rotated_at + timedelta(days=settings.tenant_api_key_expiration_days)
        return rotated_at, expires_at

    def provision_tenant(self, payload: TenantProvisionRequest) -> TenantProvisionResponse:
        if not validate_empresa_id(payload.empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )
        raw_api_key = generate_api_key()
        api_key_hash = hash_api_key(raw_api_key)
        api_key_last_rotated_at, api_key_expires_at = self._build_api_key_lifecycle()
        tenant = self.tenant_repository.upsert_tenant(
            empresa_id=payload.empresa_id,
            nome=payload.nome,
            api_key_hash=api_key_hash,
            api_key_last_rotated_at=api_key_last_rotated_at,
            api_key_expires_at=api_key_expires_at,
        )
        return TenantProvisionResponse(
            empresa_id=tenant.empresa_id,
            nome=tenant.nome,
            api_key=raw_api_key,
            api_key_last_rotated_at=tenant.api_key_last_rotated_at,
            api_key_expires_at=tenant.api_key_expires_at,
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
        api_key_last_rotated_at, api_key_expires_at = self._build_api_key_lifecycle()
        tenant = self.tenant_repository.rotate_api_key(
            empresa_id=empresa_id,
            new_api_key_hash=api_key_hash,
            api_key_last_rotated_at=api_key_last_rotated_at,
            api_key_expires_at=api_key_expires_at,
        )
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant nao encontrado.",
            )
        return TenantRotateKeyResponse(
            empresa_id=tenant.empresa_id,
            api_key=raw_api_key,
            api_key_last_rotated_at=tenant.api_key_last_rotated_at,
            api_key_expires_at=tenant.api_key_expires_at,
            status="ok",
        )

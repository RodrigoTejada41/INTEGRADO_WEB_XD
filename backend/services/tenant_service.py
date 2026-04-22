from datetime import UTC, datetime

from fastapi import HTTPException, status

from backend.config.settings import get_settings
from backend.models.tenant import Tenant
from backend.repositories.tenant_repository import TenantRepository
from backend.utils.security import validate_empresa_id, verify_api_key

settings = get_settings()


class TenantService:
    def __init__(self, repository: TenantRepository):
        self.repository = repository

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

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
        api_key_expires_at = self._normalize_datetime(tenant.api_key_expires_at)
        if (
            settings.tenant_api_key_expiration_enforced
            and api_key_expires_at is not None
            and api_key_expires_at <= datetime.now(UTC)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais expiradas.",
            )
        return tenant

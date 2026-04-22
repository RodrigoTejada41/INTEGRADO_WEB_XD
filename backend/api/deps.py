from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.config.database import get_session
from backend.config.settings import get_settings
from backend.models.tenant import Tenant
from backend.repositories.tenant_repository import TenantRepository
from backend.services.tenant_service import TenantService
from backend.utils.security import validate_api_key_format

settings = get_settings()


def get_current_tenant(
    session: Session = Depends(get_session),
    api_key: str | None = Header(default=None, alias=settings.api_key_header),
    empresa_id: str | None = Header(default=None, alias=settings.empresa_header),
) -> Tenant:
    if not api_key or not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cabecalhos de autenticacao ausentes.",
        )
    if not validate_api_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas.",
        )
    tenant_repository = TenantRepository(session)
    tenant_service = TenantService(tenant_repository)
    return tenant_service.authenticate(empresa_id=empresa_id, api_key=api_key)

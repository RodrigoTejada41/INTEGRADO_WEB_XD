from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.config.database import get_session
from backend.config.settings import get_settings
from backend.models.local_client import LocalClient
from backend.repositories.local_client_command_repository import LocalClientCommandRepository
from backend.repositories.local_client_log_repository import LocalClientLogRepository
from backend.repositories.local_client_repository import LocalClientRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.services.local_client_service import LocalClientService
from backend.utils.security import validate_api_key_format, validate_empresa_id

settings = get_settings()


def get_local_client_service(session: Session = Depends(get_session)) -> LocalClientService:
    return LocalClientService(
        client_repository=LocalClientRepository(session),
        command_repository=LocalClientCommandRepository(session),
        log_repository=LocalClientLogRepository(session),
        tenant_repository=TenantRepository(session),
    )


def get_authenticated_local_client(
    service: LocalClientService = Depends(get_local_client_service),
    client_id: str | None = Header(default=None, alias=settings.local_client_id_header),
    client_token: str | None = Header(default=None, alias=settings.local_client_token_header),
    empresa_id: str | None = Header(default=None, alias=settings.empresa_header),
) -> LocalClient:
    if not client_id or not client_token or not empresa_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local client authentication headers are missing.",
        )
    if not validate_empresa_id(empresa_id) or not validate_api_key_format(client_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Local client credentials are invalid.",
        )
    return service.authenticate_client(
        client_id=client_id,
        empresa_id=empresa_id,
        raw_token=client_token,
    )

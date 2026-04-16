from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.config.database import get_session
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.server_settings import ServerSettingsResponse, ServerSettingsUpdateRequest
from backend.schemas.tenant import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRotateKeyResponse,
)
from backend.services.admin_service import AdminService
from backend.services.server_settings_service import ServerSettingsService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/tenants", response_model=TenantProvisionResponse, dependencies=[Depends(require_admin_token)])
def create_or_update_tenant(
    payload: TenantProvisionRequest,
    session: Session = Depends(get_session),
) -> TenantProvisionResponse:
    repository = TenantRepository(session)
    service = AdminService(repository)
    result = service.provision_tenant(payload)
    session.commit()
    return result


@router.post(
    "/tenants/{empresa_id}/rotate-key",
    response_model=TenantRotateKeyResponse,
    dependencies=[Depends(require_admin_token)],
)
def rotate_tenant_key(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> TenantRotateKeyResponse:
    repository = TenantRepository(session)
    service = AdminService(repository)
    result = service.rotate_tenant_key(empresa_id=empresa_id)
    session.commit()
    return result


@router.get(
    "/server-settings",
    response_model=ServerSettingsResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_server_settings(session: Session = Depends(get_session)) -> ServerSettingsResponse:
    repository = ServerSettingRepository(session)
    service = ServerSettingsService(repository)
    return service.get_settings()


@router.put(
    "/server-settings",
    response_model=ServerSettingsResponse,
    dependencies=[Depends(require_admin_token)],
)
def update_server_settings(
    payload: ServerSettingsUpdateRequest,
    session: Session = Depends(get_session),
) -> ServerSettingsResponse:
    repository = ServerSettingRepository(session)
    service = ServerSettingsService(repository)
    result = service.update_settings(payload)
    session.commit()
    return result

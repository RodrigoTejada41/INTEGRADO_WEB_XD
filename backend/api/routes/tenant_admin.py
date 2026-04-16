from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.config.database import get_session
from backend.models.tenant_destination_config import TenantDestinationConfig
from backend.models.tenant_source_config import TenantSourceConfig
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.repositories.tenant_config_repository import TenantConfigRepository
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.server_settings import ServerSettingsResponse, ServerSettingsUpdateRequest
from backend.schemas.tenant_configs import (
    TenantConfigCreateRequest,
    TenantConfigDeleteResponse,
    TenantConfigResponse,
    TenantConfigUpdateRequest,
)
from backend.schemas.tenant_jobs import TenantJobResponse, TenantJobRetryResponse, TenantJobSummaryResponse
from backend.schemas.tenant import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRotateKeyResponse,
)
from backend.services.admin_service import AdminService
from backend.services.tenant_job_service import TenantJobService
from backend.services.server_settings_service import ServerSettingsService
from backend.services.tenant_config_service import TenantConfigService

router = APIRouter(prefix="/admin", tags=["admin"])


def _tenant_config_service(session: Session) -> TenantConfigService:
    tenant_repository = TenantRepository(session)
    source_repository = TenantConfigRepository(session, TenantSourceConfig)
    destination_repository = TenantConfigRepository(session, TenantDestinationConfig)
    return TenantConfigService(tenant_repository, source_repository, destination_repository)


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


@router.get(
    "/tenants/{empresa_id}/source-configs",
    response_model=list[TenantConfigResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_source_configs(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> list[TenantConfigResponse]:
    service = _tenant_config_service(session)
    return service.list_source_configs(empresa_id)


@router.post(
    "/tenants/{empresa_id}/source-configs",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_source_config(
    empresa_id: str,
    payload: TenantConfigCreateRequest,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    result = service.create_source_config(empresa_id, payload)
    session.commit()
    return result


@router.put(
    "/tenants/{empresa_id}/source-configs/{config_id}",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def update_source_config(
    empresa_id: str,
    config_id: str,
    payload: TenantConfigUpdateRequest,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    result = service.update_source_config(empresa_id, config_id, payload)
    session.commit()
    return result


@router.delete(
    "/tenants/{empresa_id}/source-configs/{config_id}",
    response_model=TenantConfigDeleteResponse,
    dependencies=[Depends(require_admin_token)],
)
def delete_source_config(
    empresa_id: str,
    config_id: str,
    session: Session = Depends(get_session),
) -> TenantConfigDeleteResponse:
    service = _tenant_config_service(session)
    result = service.delete_source_config(empresa_id, config_id)
    session.commit()
    return result


@router.get(
    "/tenants/{empresa_id}/destination-configs",
    response_model=list[TenantConfigResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_destination_configs(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> list[TenantConfigResponse]:
    service = _tenant_config_service(session)
    return service.list_destination_configs(empresa_id)


@router.post(
    "/tenants/{empresa_id}/destination-configs",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_destination_config(
    empresa_id: str,
    payload: TenantConfigCreateRequest,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    result = service.create_destination_config(empresa_id, payload)
    session.commit()
    return result


@router.put(
    "/tenants/{empresa_id}/destination-configs/{config_id}",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def update_destination_config(
    empresa_id: str,
    config_id: str,
    payload: TenantConfigUpdateRequest,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    result = service.update_destination_config(empresa_id, config_id, payload)
    session.commit()
    return result


@router.delete(
    "/tenants/{empresa_id}/destination-configs/{config_id}",
    response_model=TenantConfigDeleteResponse,
    dependencies=[Depends(require_admin_token)],
)
def delete_destination_config(
    empresa_id: str,
    config_id: str,
    session: Session = Depends(get_session),
) -> TenantConfigDeleteResponse:
    service = _tenant_config_service(session)
    result = service.delete_destination_config(empresa_id, config_id)
    session.commit()
    return result


@router.get(
    "/tenants/{empresa_id}/sync-jobs/summary",
    response_model=TenantJobSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_sync_jobs_summary(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> TenantJobSummaryResponse:
    service = TenantJobService(TenantSyncJobRepository(session))
    return service.get_summary(empresa_id)


@router.get(
    "/tenants/{empresa_id}/sync-jobs/dead-letter",
    response_model=list[TenantJobResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_dead_letter_jobs(
    empresa_id: str,
    limit: int = 10,
    session: Session = Depends(get_session),
) -> list[TenantJobResponse]:
    service = TenantJobService(TenantSyncJobRepository(session))
    return service.list_dead_letters(empresa_id, limit=limit)


@router.post(
    "/tenants/{empresa_id}/sync-jobs/{job_id}/retry",
    response_model=TenantJobRetryResponse,
    dependencies=[Depends(require_admin_token)],
)
def retry_sync_job(
    empresa_id: str,
    job_id: str,
    session: Session = Depends(get_session),
) -> TenantJobRetryResponse:
    repository = TenantSyncJobRepository(session)
    service = TenantJobService(repository)
    result = service.retry_job(empresa_id, job_id)
    session.commit()
    return result

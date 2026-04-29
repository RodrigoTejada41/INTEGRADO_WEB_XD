from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_tenant
from backend.config.database import get_session
from backend.models.tenant import Tenant
from backend.repositories.tenant_repository import TenantRepository
from backend.repositories.venda_repository import VendaRepository
from backend.schemas.sync import SyncRequest, SyncResponse
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.services.server_settings_service import ServerSettingsService
from backend.services.sync_service import SyncService
from backend.utils.metrics import metrics_registry

router = APIRouter(tags=["sync"])


@router.post("/sync", response_model=SyncResponse)
def sync_data(
    payload: SyncRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> SyncResponse:
    venda_repository = VendaRepository(session)
    tenant_repository = TenantRepository(session)
    setting_repository = ServerSettingRepository(session)
    server_settings = ServerSettingsService(setting_repository).get_settings()
    service = SyncService(
        venda_repository,
        tenant_repository=tenant_repository,
        ingestion_enabled=server_settings.ingestion_enabled,
        max_batch_size=server_settings.max_batch_size,
    )
    try:
        response = service.sync_batch(current_tenant.empresa_id, payload)
        session.commit()
        return response
    except HTTPException:
        session.rollback()
        metrics_registry.record_sync_failure()
        raise
    except Exception:
        session.rollback()
        metrics_registry.record_sync_failure()
        raise

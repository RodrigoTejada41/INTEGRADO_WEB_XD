from fastapi import APIRouter, Depends, Header
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_tenant
from backend.config.database import get_session
from backend.models.tenant import Tenant
from backend.repositories.local_client_repository import LocalClientRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.repositories.venda_repository import VendaRepository
from backend.schemas.sync import SyncRequest, SyncResponse, SyncStatusRequest, SyncStatusResponse
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.services.server_settings_service import ServerSettingsService
from backend.services.sync_service import SyncService
from backend.utils.metrics import metrics_registry

router = APIRouter(tags=["sync"])


def _normalize_agent_label(value: str | None) -> str:
    label = (value or "agent-local").strip()
    return label[:120] if label else "agent-local"


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


@router.post("/sync/status", response_model=SyncStatusResponse)
def sync_status(
    payload: SyncStatusRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
    agent_label: str | None = Header(default=None, alias="X-Agent-Device-Label"),
) -> SyncStatusResponse:
    repository = LocalClientRepository(session)
    client = repository.record_sync_status(
        empresa_id=current_tenant.empresa_id,
        client_label=_normalize_agent_label(agent_label),
        last_sync_at=payload.last_sync_at,
        status="online" if payload.status == "success" else "error",
        status_snapshot={
            "service": "agent_local",
            "last_sync_at": payload.last_sync_at.isoformat(),
            "last_sync_status": payload.status,
            "last_sync_reason": payload.reason or "scheduled_cycle",
            "processed_count": payload.processed_count,
        },
    )
    session.commit()
    return SyncStatusResponse(
        status="ok",
        empresa_id=current_tenant.empresa_id,
        client_id=client.id,
        last_sync_at=client.last_sync_at or payload.last_sync_at,
    )

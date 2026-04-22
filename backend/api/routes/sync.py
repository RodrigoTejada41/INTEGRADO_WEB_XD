from fastapi import APIRouter, Depends, Request
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_current_tenant
from backend.config.database import get_session
from backend.config.settings import get_settings
from backend.models.tenant import Tenant
from backend.repositories.tenant_audit_repository import TenantAuditRepository
from backend.repositories.venda_repository import VendaRepository
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.schemas.sync import SyncRequest, SyncResponse
from backend.services.server_settings_service import ServerSettingsService
from backend.services.sync_service import SyncService
from backend.utils.audit import build_request_audit_context
from backend.utils.correlation import bind_log_context
from backend.utils.metrics import metrics_registry

router = APIRouter(tags=["sync"])
settings = get_settings()


@router.post("/sync", response_model=SyncResponse)
def sync_data(
    payload: SyncRequest,
    request: Request,
    current_tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> SyncResponse:
    venda_repository = VendaRepository(session)
    setting_repository = ServerSettingRepository(session)
    server_settings = ServerSettingsService(setting_repository).get_settings()
    service = SyncService(
        venda_repository,
        ingestion_enabled=server_settings.ingestion_enabled,
        max_batch_size=server_settings.max_batch_size,
        chunk_size=settings.sync_ingest_chunk_size,
    )
    correlation_id = getattr(request.state, "correlation_id", None)
    audit_context = build_request_audit_context(request)
    with bind_log_context(
        empresa_id=current_tenant.empresa_id,
        correlation_id=correlation_id,
    ):
        try:
            response = service.sync_batch(current_tenant.empresa_id, payload)
            TenantAuditRepository(session).create(
                empresa_id=current_tenant.empresa_id,
                actor="tenant_api",
                action="sync.ingest",
                resource_type="sync_batch",
                resource_id=None,
                correlation_id=audit_context["correlation_id"] or None,
                request_path=audit_context["request_path"] or None,
                actor_ip=audit_context["actor_ip"] or None,
                user_agent=audit_context["user_agent"] or None,
                detail={
                    "records": str(response.processed_count),
                    "empresa_id": current_tenant.empresa_id,
                    "correlation_id": correlation_id or "",
                },
            )
            session.commit()
            return response
        except HTTPException:
            session.rollback()
            metrics_registry.record_sync_failure(current_tenant.empresa_id)
            raise
        except Exception:
            session.rollback()
            metrics_registry.record_sync_failure(current_tenant.empresa_id)
            raise

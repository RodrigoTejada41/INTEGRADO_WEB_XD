from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.config.database import SessionLocal, get_session
from backend.models.tenant_destination_config import TenantDestinationConfig
from backend.models.tenant_source_config import TenantSourceConfig
from backend.repositories.server_setting_repository import ServerSettingRepository
from backend.repositories.tenant_audit_repository import TenantAuditRepository
from backend.repositories.tenant_config_repository import TenantConfigRepository
from backend.repositories.tenant_sync_job_repository import TenantSyncJobRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.repositories.venda_repository import VendaRepository
from backend.schemas.tenant_audit import TenantAuditEventResponse, TenantAuditSummaryResponse
from backend.schemas.server_settings import ServerSettingsResponse, ServerSettingsUpdateRequest
from backend.schemas.secure_connection_configs import (
    SecureConnectionConfigCreateRequest,
    SecureConnectionKeyRotateRequest,
    SecureConnectionKeyRotateResponse,
    SecureConnectionSecretUpdateRequest,
    SecureConnectionSecretUpdateResponse,
    SecureConnectionConfigResponse,
)
from backend.schemas.tenant_configs import (
    TenantConfigCreateRequest,
    TenantConfigDeleteResponse,
    TenantConfigResponse,
    TenantConfigSummaryResponse,
    TenantConfigUpdateRequest,
)
from backend.schemas.tenant_jobs import TenantJobResponse, TenantJobRetryResponse, TenantJobSummaryResponse
from backend.schemas.tenant_observability import TenantObservabilityResponse
from backend.schemas.tenant_reports import (
    TenantReportBranchesResponse,
    TenantDailySalesResponse,
    TenantRecentSaleResponse,
    TenantRecentSalesResponse,
    TenantReportOverviewResponse,
    TenantTopProductResponse,
    TenantTopProductsResponse,
)
from backend.schemas.tenant import (
    TenantProvisionRequest,
    TenantProvisionResponse,
    TenantRotateKeyResponse,
)
from backend.services.admin_service import AdminService
from backend.services.tenant_audit_service import TenantAuditService
from backend.services.tenant_job_service import TenantJobService
from backend.services.tenant_report_service import TenantReportService
from backend.services.server_settings_service import ServerSettingsService
from backend.services.connection_secret_service import ConnectionSecretService
from backend.services.tenant_config_service import TenantConfigService
from backend.services.tenant_sync_scheduler import TenantSyncScheduler
from backend.utils.audit import build_request_audit_context
from backend.utils.metrics import metrics_registry

router = APIRouter(prefix="/admin", tags=["admin"])


def _tenant_config_service(session: Session) -> TenantConfigService:
    tenant_repository = TenantRepository(session)
    source_repository = TenantConfigRepository(session, TenantSourceConfig)
    destination_repository = TenantConfigRepository(session, TenantDestinationConfig)
    return TenantConfigService(tenant_repository, source_repository, destination_repository)


def _audit_service(session: Session) -> TenantAuditService:
    return TenantAuditService(TenantAuditRepository(session))


def _connection_secret_service(session: Session) -> ConnectionSecretService:
    return ConnectionSecretService(ServerSettingRepository(session))


def _tenant_report_service(session: Session) -> TenantReportService:
    return TenantReportService(TenantRepository(session), VendaRepository(session))


def _audit_context(request: Request) -> dict[str, str]:
    return build_request_audit_context(request)


def _record_admin_audit(
    *,
    session: Session,
    request: Request,
    empresa_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: dict[str, object],
    status: str = "success",
) -> None:
    audit_context = _audit_context(request)
    _audit_service(session).record(
        empresa_id=empresa_id,
        actor=request.headers.get("X-Audit-Actor", "system"),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        correlation_id=audit_context["correlation_id"] or None,
        request_path=audit_context["request_path"] or None,
        actor_ip=audit_context["actor_ip"] or None,
        user_agent=audit_context["user_agent"] or None,
        detail=detail,
    )


def _record_admin_failure(
    *,
    session: Session,
    request: Request,
    empresa_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    exc: Exception,
    detail: dict[str, object] | None = None,
) -> None:
    failure_detail = dict(detail or {})
    if isinstance(exc, HTTPException):
        failure_detail.setdefault("error", str(exc.detail))
        failure_detail.setdefault("status_code", exc.status_code)
    else:
        failure_detail.setdefault("error", "internal_server_error")
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status="failure",
        detail=failure_detail,
    )


@router.post("/tenants", response_model=TenantProvisionResponse, dependencies=[Depends(require_admin_token)])
def create_or_update_tenant(
    payload: TenantProvisionRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantProvisionResponse:
    repository = TenantRepository(session)
    service = AdminService(repository)
    try:
        result = service.provision_tenant(payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=payload.empresa_id,
            action="tenant.provision",
            resource_type="tenant",
            resource_id=payload.empresa_id,
            exc=exc,
            detail={"nome": payload.nome},
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=payload.empresa_id,
        action="tenant.provision",
        resource_type="tenant",
        resource_id=payload.empresa_id,
        detail={
            "nome": payload.nome,
            "api_key_expires_at": result.api_key_expires_at.isoformat() if result.api_key_expires_at else "",
        },
    )
    session.commit()
    return result


@router.post(
    "/tenants/{empresa_id}/rotate-key",
    response_model=TenantRotateKeyResponse,
    dependencies=[Depends(require_admin_token)],
)
def rotate_tenant_key(
    empresa_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantRotateKeyResponse:
    repository = TenantRepository(session)
    service = AdminService(repository)
    try:
        result = service.rotate_tenant_key(empresa_id=empresa_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="tenant.rotate_key",
            resource_type="tenant",
            resource_id=empresa_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="tenant.rotate_key",
        resource_type="tenant",
        resource_id=empresa_id,
        detail={
            "status": "rotated",
            "api_key_expires_at": result.api_key_expires_at.isoformat() if result.api_key_expires_at else "",
        },
    )
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
    request: Request,
    session: Session = Depends(get_session),
) -> ServerSettingsResponse:
    repository = ServerSettingRepository(session)
    service = ServerSettingsService(repository)
    try:
        result = service.update_settings(payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id="__global__",
            action="server_settings.update",
            resource_type="server_settings",
            resource_id="global",
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id="__global__",
        action="server_settings.update",
        resource_type="server_settings",
        resource_id="global",
        detail={
            "ingestion_enabled": str(payload.ingestion_enabled).lower(),
            "max_batch_size": str(payload.max_batch_size),
            "retention_mode": payload.retention_mode,
            "retention_months": str(payload.retention_months),
            "connection_secrets_file": payload.connection_secrets_file,
        },
    )
    session.commit()
    return result


@router.post(
    "/tenants/{empresa_id}/secure-configs",
    response_model=SecureConnectionConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_secure_connection_config(
    empresa_id: str,
    payload: SecureConnectionConfigCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SecureConnectionConfigResponse:
    config_service = _tenant_config_service(session)
    secret_service = _connection_secret_service(session)
    try:
        settings_key, secrets_file, generated_access_key = secret_service.create_secret_reference(
            secret_settings=payload.secret_settings,
            generate_access_key=payload.generate_access_key,
            access_key_field=payload.access_key_field,
        )
        config_settings = dict(payload.settings)
        config_settings["settings_file"] = secrets_file
        config_settings["settings_key"] = settings_key
        config_request = TenantConfigCreateRequest(
            nome=payload.nome,
            connector_type=payload.connector_type,
            sync_interval_minutes=payload.sync_interval_minutes,
            settings=config_settings,
        )
        if payload.scope == "source":
            config = config_service.create_source_config(empresa_id, config_request)
            action = "source_config.secure_create"
            resource_type = "source_config"
        else:
            config = config_service.create_destination_config(empresa_id, config_request)
            action = "destination_config.secure_create"
            resource_type = "destination_config"
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="secure_config.create",
            resource_type="secure_config",
            resource_id="pending",
            exc=exc,
            detail={
                "scope": payload.scope,
                "nome": payload.nome,
                "connector_type": payload.connector_type,
            },
        )
        session.commit()
        raise

    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action=action,
        resource_type=resource_type,
        resource_id=config.id,
        detail={
            "nome": payload.nome,
            "connector_type": payload.connector_type,
            "settings_key": settings_key,
            "secrets_file": secrets_file,
            "generated_access_key": "true" if generated_access_key else "false",
        },
    )
    session.commit()
    return SecureConnectionConfigResponse(
        scope=payload.scope,
        settings_key=settings_key,
        secrets_file=secrets_file,
        generated_access_key=generated_access_key,
        config=config,
    )


@router.post(
    "/tenants/{empresa_id}/secure-configs/{settings_key}/rotate-key",
    response_model=SecureConnectionKeyRotateResponse,
    dependencies=[Depends(require_admin_token)],
)
def rotate_secure_connection_key(
    empresa_id: str,
    settings_key: str,
    payload: SecureConnectionKeyRotateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SecureConnectionKeyRotateResponse:
    secret_service = _connection_secret_service(session)
    try:
        secrets_file, access_key_field, generated_access_key = secret_service.rotate_access_key(
            settings_key=settings_key,
            access_key_field=payload.access_key_field,
        )
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="secure_config.rotate_key",
            resource_type="secure_config",
            resource_id=settings_key,
            exc=exc,
            detail={"settings_key": settings_key},
        )
        session.commit()
        raise

    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="secure_config.rotate_key",
        resource_type="secure_config",
        resource_id=settings_key,
        detail={
            "settings_key": settings_key,
            "access_key_field": access_key_field,
            "secrets_file": secrets_file,
        },
    )
    session.commit()
    return SecureConnectionKeyRotateResponse(
        settings_key=settings_key,
        secrets_file=secrets_file,
        access_key_field=access_key_field,
        generated_access_key=generated_access_key,
    )


@router.post(
    "/tenants/{empresa_id}/secure-configs/{settings_key}/update-secret",
    response_model=SecureConnectionSecretUpdateResponse,
    dependencies=[Depends(require_admin_token)],
)
def update_secure_connection_secret(
    empresa_id: str,
    settings_key: str,
    payload: SecureConnectionSecretUpdateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SecureConnectionSecretUpdateResponse:
    secret_service = _connection_secret_service(session)
    try:
        secrets_file, updated_fields = secret_service.update_secret_entry(
            settings_key=settings_key,
            secret_settings=payload.secret_settings,
            merge=payload.merge,
        )
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="secure_config.update_secret",
            resource_type="secure_config",
            resource_id=settings_key,
            exc=exc,
            detail={"settings_key": settings_key},
        )
        session.commit()
        raise

    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="secure_config.update_secret",
        resource_type="secure_config",
        resource_id=settings_key,
        detail={
            "settings_key": settings_key,
            "updated_fields": ",".join(updated_fields),
            "merge": "true" if payload.merge else "false",
            "secrets_file": secrets_file,
        },
    )
    session.commit()
    return SecureConnectionSecretUpdateResponse(
        settings_key=settings_key,
        secrets_file=secrets_file,
        updated_fields=updated_fields,
    )


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


@router.get(
    "/tenants/{empresa_id}/source-configs/summary",
    response_model=TenantConfigSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_source_configs_summary(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> TenantConfigSummaryResponse:
    service = _tenant_config_service(session)
    return service.get_source_summary(empresa_id)


@router.post(
    "/tenants/{empresa_id}/source-configs",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_source_config(
    empresa_id: str,
    payload: TenantConfigCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    try:
        result = service.create_source_config(empresa_id, payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="source_config.create",
            resource_type="source_config",
            resource_id="pending",
            exc=exc,
            detail={"nome": payload.nome, "connector_type": payload.connector_type},
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="source_config.create",
        resource_type="source_config",
        resource_id=result.id,
        detail={"nome": payload.nome, "connector_type": payload.connector_type},
    )
    session.commit()
    return result


@router.post(
    "/tenants/{empresa_id}/source-configs/sync-all",
    response_model=TenantConfigSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def trigger_all_source_configs_sync(
    empresa_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigSummaryResponse:
    service = _tenant_config_service(session)
    scheduler = TenantSyncScheduler(SessionLocal, AsyncIOScheduler(timezone="UTC"))
    try:
        scheduler.sync_all_jobs()
        result = service.get_source_summary(empresa_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="source_config.sync_all",
            resource_type="source_config",
            resource_id=empresa_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="source_config.sync_all",
        resource_type="source_config",
        resource_id=empresa_id,
        detail={
            "total_count": str(result.total_count),
            "active_count": str(result.active_count),
            "pending_count": str(result.pending_count),
        },
    )
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
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    try:
        result = service.update_source_config(empresa_id, config_id, payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="source_config.update",
            resource_type="source_config",
            resource_id=config_id,
            exc=exc,
            detail={"nome": payload.nome or "", "connector_type": payload.connector_type or ""},
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="source_config.update",
        resource_type="source_config",
        resource_id=config_id,
        detail={"nome": payload.nome or "", "connector_type": payload.connector_type or ""},
    )
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
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigDeleteResponse:
    service = _tenant_config_service(session)
    try:
        result = service.delete_source_config(empresa_id, config_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="source_config.delete",
            resource_type="source_config",
            resource_id=config_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="source_config.delete",
        resource_type="source_config",
        resource_id=config_id,
        detail={"status": "deleted"},
    )
    session.commit()
    return result


@router.post(
    "/tenants/{empresa_id}/source-configs/{config_id}/sync",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def trigger_source_config_sync(
    empresa_id: str,
    config_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    try:
        config = service.get_source_config(empresa_id, config_id)
        if not config.ativo:
            raise HTTPException(status_code=400, detail="Configuracao inativa.")
        scheduler = TenantSyncScheduler(SessionLocal, AsyncIOScheduler(timezone="UTC"))
        scheduler.run_source_sync(config_id)
        result = service.get_source_config(empresa_id, config_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="source_config.sync_now",
            resource_type="source_config",
            resource_id=config_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="source_config.sync_now",
        resource_type="source_config",
        resource_id=config_id,
        detail={"status": "queued", "last_status": result.last_status},
    )
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


@router.get(
    "/tenants/{empresa_id}/destination-configs/summary",
    response_model=TenantConfigSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_destination_configs_summary(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> TenantConfigSummaryResponse:
    service = _tenant_config_service(session)
    return service.get_destination_summary(empresa_id)


@router.post(
    "/tenants/{empresa_id}/destination-configs",
    response_model=TenantConfigResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_destination_config(
    empresa_id: str,
    payload: TenantConfigCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    try:
        result = service.create_destination_config(empresa_id, payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="destination_config.create",
            resource_type="destination_config",
            resource_id="pending",
            exc=exc,
            detail={"nome": payload.nome, "connector_type": payload.connector_type},
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="destination_config.create",
        resource_type="destination_config",
        resource_id=result.id,
        detail={"nome": payload.nome, "connector_type": payload.connector_type},
    )
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
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigResponse:
    service = _tenant_config_service(session)
    try:
        result = service.update_destination_config(empresa_id, config_id, payload)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="destination_config.update",
            resource_type="destination_config",
            resource_id=config_id,
            exc=exc,
            detail={"nome": payload.nome or "", "connector_type": payload.connector_type or ""},
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="destination_config.update",
        resource_type="destination_config",
        resource_id=config_id,
        detail={"nome": payload.nome or "", "connector_type": payload.connector_type or ""},
    )
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
    request: Request,
    session: Session = Depends(get_session),
) -> TenantConfigDeleteResponse:
    service = _tenant_config_service(session)
    try:
        result = service.delete_destination_config(empresa_id, config_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="destination_config.delete",
            resource_type="destination_config",
            resource_id=config_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="destination_config.delete",
        resource_type="destination_config",
        resource_id=config_id,
        detail={"status": "deleted"},
    )
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
    "/tenants/{empresa_id}/sync-jobs",
    response_model=list[TenantJobResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_sync_jobs(
    empresa_id: str,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[TenantJobResponse]:
    service = TenantJobService(TenantSyncJobRepository(session))
    return service.list_jobs(empresa_id, limit=limit)


@router.get(
    "/tenants/{empresa_id}/observability",
    response_model=TenantObservabilityResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_tenant_observability(empresa_id: str) -> TenantObservabilityResponse:
    snapshot = metrics_registry.snapshot_tenant(empresa_id)
    return TenantObservabilityResponse(empresa_id=empresa_id, **snapshot)


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
    request: Request,
    session: Session = Depends(get_session),
) -> TenantJobRetryResponse:
    repository = TenantSyncJobRepository(session)
    service = TenantJobService(repository)
    try:
        result = service.retry_job(empresa_id, job_id)
    except Exception as exc:
        session.rollback()
        _record_admin_failure(
            session=session,
            request=request,
            empresa_id=empresa_id,
            action="sync_job.retry",
            resource_type="sync_job",
            resource_id=job_id,
            exc=exc,
        )
        session.commit()
        raise
    _record_admin_audit(
        session=session,
        request=request,
        empresa_id=empresa_id,
        action="sync_job.retry",
        resource_type="sync_job",
        resource_id=job_id,
        detail={"status": result.status},
    )
    session.commit()
    return result


@router.get(
    "/tenants/{empresa_id}/audit/summary",
    response_model=TenantAuditSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_audit_summary(
    empresa_id: str,
    session: Session = Depends(get_session),
) -> TenantAuditSummaryResponse:
    service = _audit_service(session)
    return service.summary(empresa_id)


@router.get(
    "/tenants/{empresa_id}/audit/events",
    response_model=list[TenantAuditEventResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_audit_events(
    empresa_id: str,
    limit: int = 10,
    session: Session = Depends(get_session),
) -> list[TenantAuditEventResponse]:
    service = _audit_service(session)
    return service.list_recent(empresa_id, limit=limit)


@router.get(
    "/tenants/{empresa_id}/reports/overview",
    response_model=TenantReportOverviewResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_report_overview(
    empresa_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    session: Session = Depends(get_session),
) -> TenantReportOverviewResponse:
    service = _tenant_report_service(session)
    snapshot = service.get_overview(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    return TenantReportOverviewResponse(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        **snapshot,
    )


@router.get(
    "/tenants/{empresa_id}/reports/daily-sales",
    response_model=TenantDailySalesResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_daily_sales_report(
    empresa_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    session: Session = Depends(get_session),
) -> TenantDailySalesResponse:
    service = _tenant_report_service(session)
    items = service.get_daily_sales(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    return TenantDailySalesResponse(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        items=items,
    )


@router.get(
    "/tenants/{empresa_id}/reports/top-products",
    response_model=TenantTopProductsResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_top_products_report(
    empresa_id: str,
    limit: int = 10,
    start_date: date | None = None,
    end_date: date | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    session: Session = Depends(get_session),
) -> TenantTopProductsResponse:
    service = _tenant_report_service(session)
    items = service.get_top_products(
        empresa_id=empresa_id,
        limit=max(1, min(limit, 100)),
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    return TenantTopProductsResponse(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        limit=max(1, min(limit, 100)),
        items=[TenantTopProductResponse(**item) for item in items],
    )


@router.get(
    "/tenants/{empresa_id}/reports/recent-sales",
    response_model=TenantRecentSalesResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_recent_sales_report(
    empresa_id: str,
    limit: int = 20,
    start_date: date | None = None,
    end_date: date | None = None,
    branch_code: str | None = None,
    terminal_code: str | None = None,
    session: Session = Depends(get_session),
) -> TenantRecentSalesResponse:
    service = _tenant_report_service(session)
    bounded_limit = max(1, min(limit, 200))
    items = service.get_recent_sales(
        empresa_id=empresa_id,
        limit=bounded_limit,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
    )
    return TenantRecentSalesResponse(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        branch_code=branch_code,
        terminal_code=terminal_code,
        limit=bounded_limit,
        items=[TenantRecentSaleResponse.model_validate(item) for item in items],
    )


@router.get(
    "/tenants/{empresa_id}/reports/branches",
    response_model=TenantReportBranchesResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_report_branches(
    empresa_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    terminal_code: str | None = None,
    session: Session = Depends(get_session),
) -> TenantReportBranchesResponse:
    service = _tenant_report_service(session)
    items = service.get_branch_codes(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
    )
    return TenantReportBranchesResponse(
        empresa_id=empresa_id,
        start_date=start_date,
        end_date=end_date,
        terminal_code=terminal_code,
        items=items,
    )

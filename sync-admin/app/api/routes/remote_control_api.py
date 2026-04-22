from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.db import get_db
from app.models.sync_batch import SyncBatch
from app.models.sync_record import SyncRecord
from app.schemas.remote_control import ForceSyncResponse, LocalConfigResponse, LocalConfigUpdateRequest, LocalStatusResponse
from app.services.local_config_service import LocalConfigService
from app.services.remote_agent_service import RemoteAgentService

router = APIRouter(prefix='/api/v1', tags=['remote-control'])


def require_local_control_token(
    request: Request,
    db: Session = Depends(get_db),
    local_token: str | None = Header(default=None, alias=settings.remote_control_token_header),
) -> LocalConfigService:
    service = LocalConfigService(db)
    service.bootstrap()
    source_ip = request.client.host if request.client else None
    service.verify_control_token(local_token or '', source_ip=source_ip)
    return service


@router.get('/config', response_model=LocalConfigResponse)
def get_local_config(
    service: LocalConfigService = Depends(require_local_control_token),
) -> LocalConfigResponse:
    return LocalConfigResponse(**service.get_public_config())


@router.post('/config', response_model=LocalConfigResponse)
def update_local_config(
    payload: LocalConfigUpdateRequest,
    service: LocalConfigService = Depends(require_local_control_token),
) -> LocalConfigResponse:
    updated = service.update_public_config(payload.model_dump(exclude_none=True))
    return LocalConfigResponse(**updated)


@router.post('/sync/force', response_model=ForceSyncResponse)
def force_sync(
    db: Session = Depends(get_db),
    _: LocalConfigService = Depends(require_local_control_token),
) -> ForceSyncResponse:
    service = RemoteAgentService(db)
    result = service.perform_sync_cycle(reason='local_api')
    return ForceSyncResponse(
        status=str(result['status']),
        detail=str(result['detail']),
        last_sync_at=_parse_datetime(result.get('last_sync_at')),
    )


@router.get('/status', response_model=LocalStatusResponse)
def get_local_status(
    db: Session = Depends(get_db),
    config_service: LocalConfigService = Depends(require_local_control_token),
) -> LocalStatusResponse:
    public_config = config_service.get_public_config()
    started_at_raw = config_service.repository.get_value('started_at')
    if not started_at_raw:
        config_service.record_state('started_at', datetime.now(UTC).isoformat())
        started_at_raw = config_service.repository.get_value('started_at')
    started_at = _parse_datetime(started_at_raw) or datetime.now(UTC)

    pending_batches = db.scalar(select(func.count()).select_from(SyncBatch)) or 0
    total_records = db.scalar(select(func.count()).select_from(SyncRecord)) or 0
    return LocalStatusResponse(
        service='sync-admin',
        installation_id=str(public_config['installation_id']),
        empresa_id=str(public_config['empresa_id']),
        hostname=config_service.hostname(),
        uptime_seconds=max(0, int((datetime.now(UTC) - started_at).total_seconds())),
        started_at=started_at,
        last_sync_at=_parse_datetime(config_service.repository.get_value('last_sync_at')),
        last_sync_status=config_service.repository.get_value('last_sync_status'),
        last_sync_reason=config_service.repository.get_value('last_sync_reason'),
        last_registration_at=_parse_datetime(config_service.repository.get_value('last_registration_at')),
        last_command_poll_at=_parse_datetime(config_service.repository.get_value('last_command_poll_at')),
        last_command_origin=config_service.repository.get_value('last_command_origin'),
        pending_local_batches=int(pending_batches),
        total_local_records=int(total_records),
    )


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

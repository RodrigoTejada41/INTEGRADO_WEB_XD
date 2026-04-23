from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.api.client_deps import get_authenticated_local_client, get_local_client_service
from backend.api.deps import get_current_tenant
from backend.config.database import get_session
from backend.models.local_client import LocalClient
from backend.models.tenant import Tenant
from backend.schemas.local_client import (
    LocalClientActionResponse,
    LocalClientCommandPayload,
    LocalClientCommandResultRequest,
    LocalClientConfigUpdateRequest,
    LocalClientFleetSummaryResponse,
    LocalClientHeartbeatRequest,
    LocalClientLogResponse,
    LocalClientRegistrationRequest,
    LocalClientRegistrationResponse,
    LocalClientResponse,
)
from backend.services.local_client_service import LocalClientService

router = APIRouter(prefix="/api/v1", tags=["remote-clients"])


def _to_client_response(service: LocalClientService, client: LocalClient) -> LocalClientResponse:
    return LocalClientResponse(
        id=client.id,
        empresa_id=client.empresa_id,
        empresa_nome=service.get_empresa_nome(client.empresa_id),
        hostname=client.hostname,
        ip_address=client.ip_address,
        endpoint_url=client.endpoint_url,
        status=client.status,
        last_seen_at=client.last_seen_at,
        last_sync_at=client.last_sync_at,
        last_command_poll_at=client.last_command_poll_at,
        config_snapshot=service.parse_snapshot(client.last_config_json),
        status_snapshot=service.parse_snapshot(client.last_status_json),
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


@router.post("/register", response_model=LocalClientRegistrationResponse)
def register_local_client(
    payload: LocalClientRegistrationRequest,
    tenant: Tenant = Depends(get_current_tenant),
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> LocalClientRegistrationResponse:
    client = service.register_client(
        empresa_id=tenant.empresa_id,
        client_id=payload.client_id,
        hostname=payload.hostname,
        ip_address=payload.ip,
        endpoint_url=payload.endpoint_url,
        raw_token=payload.token,
        token_expires_at=payload.token_expires_at,
        config_snapshot=payload.config_snapshot,
        status_snapshot=payload.status_snapshot,
    )
    session.commit()
    return LocalClientRegistrationResponse(
        status="registered",
        client_id=client.id,
        empresa_id=client.empresa_id,
        token_expires_at=client.token_expires_at,
    )


@router.post("/clients/me/heartbeat", response_model=LocalClientRegistrationResponse)
def client_heartbeat(
    payload: LocalClientHeartbeatRequest,
    client: LocalClient = Depends(get_authenticated_local_client),
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> LocalClientRegistrationResponse:
    updated = service.heartbeat(
        client,
        config_snapshot=payload.config_snapshot,
        status_snapshot=payload.status_snapshot,
    )
    session.commit()
    return LocalClientRegistrationResponse(
        status="heartbeat_received",
        client_id=updated.id,
        empresa_id=updated.empresa_id,
        token_expires_at=updated.token_expires_at,
    )


@router.get("/commands", response_model=list[LocalClientCommandPayload])
def pull_commands(
    client: LocalClient = Depends(get_authenticated_local_client),
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> list[LocalClientCommandPayload]:
    commands = service.pull_commands(client)
    session.commit()
    return [
        LocalClientCommandPayload(
            id=item.id,
            client_id=item.client_id,
            empresa_id=item.empresa_id,
            command_type=item.command_type,
            payload=service.parse_snapshot(item.payload_json),
            status=item.status,
            requested_by=item.requested_by,
            origin=item.origin,
            created_at=item.created_at,
            delivered_at=item.delivered_at,
            executed_at=item.executed_at,
        )
        for item in commands
    ]


@router.post("/commands/{command_id}/result", response_model=LocalClientActionResponse)
def post_command_result(
    command_id: str,
    payload: LocalClientCommandResultRequest,
    client: LocalClient = Depends(get_authenticated_local_client),
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> LocalClientActionResponse:
    command = service.record_command_result(
        client,
        command_id=command_id,
        execution_status=payload.status,
        result=payload.result,
        config_snapshot=payload.config_snapshot,
        status_snapshot=payload.status_snapshot,
    )
    session.commit()
    return LocalClientActionResponse(
        status=payload.status,
        client_id=client.id,
        command_id=command.id,
    )


@router.get("/clients", response_model=list[LocalClientResponse], dependencies=[Depends(require_admin_token)])
def list_clients(
    empresa_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    service: LocalClientService = Depends(get_local_client_service),
) -> list[LocalClientResponse]:
    return [
        _to_client_response(service, client)
        for client in service.list_clients(empresa_id=empresa_id, status=status, search=search)
    ]


@router.get(
    "/clients/summary",
    response_model=LocalClientFleetSummaryResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_clients_summary(
    empresa_id: str | None = None,
    status: str | None = None,
    search: str | None = None,
    service: LocalClientService = Depends(get_local_client_service),
) -> LocalClientFleetSummaryResponse:
    return LocalClientFleetSummaryResponse(
        **service.summarize_clients(empresa_id=empresa_id, status=status, search=search)
    )


@router.get(
    "/clients/{client_id}/config",
    response_model=LocalClientResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_client_config(
    client_id: str,
    service: LocalClientService = Depends(get_local_client_service),
) -> LocalClientResponse:
    return _to_client_response(service, service.get_client(client_id))


@router.post(
    "/clients/{client_id}/config",
    response_model=LocalClientActionResponse,
    dependencies=[Depends(require_admin_token)],
)
def update_client_config(
    client_id: str,
    payload: LocalClientConfigUpdateRequest,
    request: Request,
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> LocalClientActionResponse:
    actor = request.headers.get("X-Audit-Actor", "system")
    client, command = service.enqueue_config_update(client_id, payload.payload, actor)
    session.commit()
    return LocalClientActionResponse(status="queued", client_id=client.id, command_id=command.id)


@router.post(
    "/clients/{client_id}/sync",
    response_model=LocalClientActionResponse,
    dependencies=[Depends(require_admin_token)],
)
def force_client_sync(
    client_id: str,
    request: Request,
    service: LocalClientService = Depends(get_local_client_service),
    session: Session = Depends(get_session),
) -> LocalClientActionResponse:
    actor = request.headers.get("X-Audit-Actor", "system")
    client, command = service.enqueue_force_sync(client_id, actor)
    session.commit()
    return LocalClientActionResponse(status="queued", client_id=client.id, command_id=command.id)


@router.get(
    "/clients/{client_id}/logs",
    response_model=list[LocalClientLogResponse],
    dependencies=[Depends(require_admin_token)],
)
def list_client_logs(
    client_id: str,
    limit: int = 20,
    service: LocalClientService = Depends(get_local_client_service),
) -> list[LocalClientLogResponse]:
    responses: list[LocalClientLogResponse] = []
    for log in service.list_logs(client_id, limit=limit):
        detail = service.parse_snapshot(log.detail_json)
        responses.append(
            LocalClientLogResponse(
                id=log.id,
                client_id=log.client_id,
                empresa_id=log.empresa_id,
                direction=log.direction,
                event_type=log.event_type,
                origin=log.origin,
                status=log.status,
                message=log.message,
                correlation_id=detail.get("correlation_id"),
                detail=detail,
                created_at=log.created_at,
            )
        )
    return responses

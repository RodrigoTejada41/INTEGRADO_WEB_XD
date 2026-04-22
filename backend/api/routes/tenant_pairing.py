from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.admin_deps import require_admin_token
from backend.config.database import get_session
from backend.repositories.tenant_agent_credential_repository import TenantAgentCredentialRepository
from backend.repositories.tenant_audit_repository import TenantAuditRepository
from backend.repositories.tenant_pairing_repository import TenantPairingRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.tenant_pairing import (
    TenantPairingActivateRequest,
    TenantPairingActivateResponse,
    TenantPairingCodeCreateRequest,
    TenantPairingCodeCreateResponse,
)
from backend.services.tenant_audit_service import TenantAuditService
from backend.services.tenant_pairing_service import TenantPairingService

router = APIRouter(tags=["tenant_pairing"])


def _service(session: Session) -> TenantPairingService:
    return TenantPairingService(
        tenant_repository=TenantRepository(session),
        pairing_repository=TenantPairingRepository(session),
        credential_repository=TenantAgentCredentialRepository(session),
    )


def _audit_service(session: Session) -> TenantAuditService:
    return TenantAuditService(TenantAuditRepository(session))


@router.post(
    "/admin/tenants/{empresa_id}/pairing-codes",
    response_model=TenantPairingCodeCreateResponse,
    dependencies=[Depends(require_admin_token)],
)
def create_pairing_code(
    empresa_id: str,
    payload: TenantPairingCodeCreateRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> TenantPairingCodeCreateResponse:
    actor = request.headers.get("X-Audit-Actor", "system")
    result = _service(session).create_pairing_code(
        empresa_id=empresa_id,
        ttl_minutes=payload.ttl_minutes,
        actor=actor,
    )
    _audit_service(session).record(
        empresa_id=empresa_id,
        actor=actor,
        action="tenant.pairing_code.create",
        resource_type="tenant_pairing_code",
        resource_id=result.empresa_id,
        detail={"ttl_minutes": str(payload.ttl_minutes)},
    )
    session.commit()
    return result


@router.post("/agent/pairings/activate", response_model=TenantPairingActivateResponse)
def activate_pairing_code(
    payload: TenantPairingActivateRequest,
    session: Session = Depends(get_session),
) -> TenantPairingActivateResponse:
    result = _service(session).activate_pairing_code(
        pairing_code=payload.pairing_code,
        device_label=payload.device_label,
    )
    _audit_service(session).record(
        empresa_id=result.empresa_id,
        actor=payload.device_label,
        action="tenant.pairing_code.consume",
        resource_type="tenant_pairing_code",
        resource_id=result.empresa_id,
        detail={"device_label": payload.device_label},
    )
    session.commit()
    return result

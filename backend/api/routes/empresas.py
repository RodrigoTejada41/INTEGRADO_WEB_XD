from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.api.auth_deps import AuthContext, require_admin_or_manager, require_superadmin
from backend.config.database import get_session
from backend.repositories.audit_log_repository import AuditLogRepository
from backend.repositories.empresa_repository import EmpresaRepository
from backend.schemas.empresa import EmpresaCreateRequest, EmpresaResponse, EmpresaUpdateRequest
from backend.services.audit_log_service import AuditLogService
from backend.services.empresa_service import EmpresaService

router = APIRouter(prefix="/api/v1/empresas", tags=["empresas"])


@router.get("", response_model=list[EmpresaResponse])
def list_empresas(
    auth: AuthContext = Depends(require_admin_or_manager),
    session: Session = Depends(get_session),
) -> list[EmpresaResponse]:
    service = EmpresaService(EmpresaRepository(session))
    empresas = service.list_empresas()
    if auth.role != "superadmin":
        empresas = [empresa for empresa in empresas if empresa.id == auth.empresa_id]
    return [EmpresaResponse(id=e.id, cnpj=e.cnpj, nome=e.nome, ativo=e.ativo) for e in empresas]


@router.post("", response_model=EmpresaResponse)
def create_empresa(
    payload: EmpresaCreateRequest,
    auth: AuthContext = Depends(require_superadmin),
    session: Session = Depends(get_session),
) -> EmpresaResponse:
    service = EmpresaService(EmpresaRepository(session))
    empresa = service.create_empresa(payload)
    AuditLogService(AuditLogRepository(session)).log(
        auth.empresa_id, auth.user_id, "empresa.create", "empresa", {"empresa_id": empresa.id, "cnpj": empresa.cnpj}
    )
    session.commit()
    return EmpresaResponse(id=empresa.id, cnpj=empresa.cnpj, nome=empresa.nome, ativo=empresa.ativo)


@router.put("/{empresa_id}", response_model=EmpresaResponse)
def update_empresa(
    empresa_id: str,
    payload: EmpresaUpdateRequest,
    auth: AuthContext = Depends(require_admin_or_manager),
    session: Session = Depends(get_session),
) -> EmpresaResponse:
    if auth.role != "superadmin" and auth.empresa_id != empresa_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant isolation violation")
    service = EmpresaService(EmpresaRepository(session))
    empresa = service.update_empresa(empresa_id, payload)
    AuditLogService(AuditLogRepository(session)).log(
        auth.empresa_id, auth.user_id, "empresa.update", "empresa", {"empresa_id": empresa.id}
    )
    session.commit()
    return EmpresaResponse(id=empresa.id, cnpj=empresa.cnpj, nome=empresa.nome, ativo=empresa.ativo)

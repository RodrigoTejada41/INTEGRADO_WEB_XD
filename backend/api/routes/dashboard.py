from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.auth_deps import AuthContext, require_authenticated_user
from backend.config.database import get_session
from backend.models.empresa import Empresa
from backend.models.user_account import UserAccount
from backend.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_summary(
    auth: AuthContext = Depends(require_authenticated_user),
    session: Session = Depends(get_session),
) -> DashboardSummaryResponse:
    empresa_filter = Empresa.id == auth.empresa_id if auth.role != "superadmin" else True
    user_filter = UserAccount.empresa_id == auth.empresa_id if auth.role != "superadmin" else True
    empresas = session.scalar(select(func.count()).select_from(Empresa).where(empresa_filter)) or 0
    usuarios = session.scalar(select(func.count()).select_from(UserAccount).where(user_filter)) or 0
    ativos = session.scalar(
        select(func.count()).select_from(UserAccount).where(user_filter, UserAccount.ativo.is_(True))
    ) or 0
    return DashboardSummaryResponse(empresas=empresas, usuarios=usuarios, ativos=ativos)

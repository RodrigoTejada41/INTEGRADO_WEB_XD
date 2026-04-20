from backend.api.routes.auth import router as auth_router
from backend.api.routes.dashboard import router as dashboard_router
from backend.api.routes.empresas import router as empresas_router
from backend.api.routes.health import router as health_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.sync import router as sync_router
from backend.api.routes.tenant_admin import router as tenant_admin_router
from backend.api.routes.usuarios import router as usuarios_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "empresas_router",
    "health_router",
    "metrics_router",
    "sync_router",
    "tenant_admin_router",
    "usuarios_router",
]

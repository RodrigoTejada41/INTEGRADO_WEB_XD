from backend.api.routes.health import router as health_router
from backend.api.routes.memory import router as memory_router
from backend.api.routes.metrics import router as metrics_router
from backend.api.routes.remote_clients import router as remote_clients_router
from backend.api.routes.sync import router as sync_router
from backend.api.routes.tenant_admin import router as tenant_admin_router

__all__ = [
    "health_router",
    "memory_router",
    "metrics_router",
    "remote_clients_router",
    "sync_router",
    "tenant_admin_router",
]

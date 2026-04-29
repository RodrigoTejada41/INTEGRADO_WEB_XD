from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "AdminService": "backend.services.admin_service",
    "RetentionService": "backend.services.retention_service",
    "ServerSettingsService": "backend.services.server_settings_service",
    "SyncService": "backend.services.sync_service",
    "TenantAuditService": "backend.services.tenant_audit_service",
    "TenantDestinationDispatcher": "backend.services.tenant_destination_dispatcher",
    "TenantPairingService": "backend.services.tenant_pairing_service",
    "TenantService": "backend.services.tenant_service",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    return getattr(module, name)

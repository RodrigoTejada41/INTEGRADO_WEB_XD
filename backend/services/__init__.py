from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "AdminService",
    "RetentionService",
    "ServerSettingsService",
    "SyncService",
    "TenantAuditService",
    "TenantDestinationDispatcher",
    "TenantReportService",
    "TenantService",
]

_SERVICE_MODULES = {
    "AdminService": "backend.services.admin_service",
    "RetentionService": "backend.services.retention_service",
    "ServerSettingsService": "backend.services.server_settings_service",
    "SyncService": "backend.services.sync_service",
    "TenantAuditService": "backend.services.tenant_audit_service",
    "TenantDestinationDispatcher": "backend.services.tenant_destination_dispatcher",
    "TenantReportService": "backend.services.tenant_report_service",
    "TenantService": "backend.services.tenant_service",
}


def __getattr__(name: str) -> Any:
    module_name = _SERVICE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)

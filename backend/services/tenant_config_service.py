from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status

from backend.connectors.registry import get_default_connector_registry
from backend.repositories.tenant_config_repository import TenantConfigRepository
from backend.repositories.tenant_repository import TenantRepository
from backend.schemas.tenant_configs import (
    TenantConfigCreateRequest,
    TenantConfigDeleteResponse,
    TenantConfigResponse,
    TenantConfigUpdateRequest,
    TenantConfigSummaryResponse,
)
from backend.utils.crypto import decrypt_json, encrypt_json
from backend.utils.security import validate_empresa_id


class TenantConfigService:
    def __init__(
        self,
        tenant_repository: TenantRepository,
        source_repository: TenantConfigRepository,
        destination_repository: TenantConfigRepository,
    ):
        self.tenant_repository = tenant_repository
        self.source_repository = source_repository
        self.destination_repository = destination_repository
        self.connector_registry = get_default_connector_registry()

    def _ensure_connector_supported(self, connector_type: str, direction: str) -> None:
        if not self.connector_registry.is_supported_for(direction, connector_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="connector_type nao suportado.",
            )

    def _ensure_tenant_exists(self, empresa_id: str) -> None:
        if not validate_empresa_id(empresa_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="empresa_id invalido.",
            )
        tenant = self.tenant_repository.get_active_tenant(empresa_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant nao encontrado.",
            )

    @staticmethod
    def _to_json(settings: dict[str, str]) -> str:
        return encrypt_json(settings)

    @staticmethod
    def _from_json(settings_json: str) -> dict[str, str]:
        return decrypt_json(settings_json)

    @staticmethod
    def _to_response(item: object, empresa_id: str) -> TenantConfigResponse:
        return TenantConfigResponse(
            id=getattr(item, "id"),
            empresa_id=empresa_id,
            nome=getattr(item, "nome"),
            connector_type=getattr(item, "connector_type"),
            sync_interval_minutes=getattr(item, "sync_interval_minutes"),
            settings=TenantConfigService._from_json(getattr(item, "settings_json")),
            ativo=getattr(item, "ativo"),
            last_run_at=getattr(item, "last_run_at"),
            last_status=getattr(item, "last_status"),
            last_error=getattr(item, "last_error"),
            created_at=getattr(item, "created_at"),
            updated_at=getattr(item, "updated_at"),
        )

    def list_source_configs(self, empresa_id: str) -> list[TenantConfigResponse]:
        self._ensure_tenant_exists(empresa_id)
        configs = self.source_repository.list_by_empresa_id(empresa_id)
        return [self._to_response(config, empresa_id) for config in configs]

    def list_destination_configs(self, empresa_id: str) -> list[TenantConfigResponse]:
        self._ensure_tenant_exists(empresa_id)
        configs = self.destination_repository.list_by_empresa_id(empresa_id)
        return [self._to_response(config, empresa_id) for config in configs]

    @staticmethod
    def _to_summary(empresa_id: str, scope: str, summary: dict[str, object]) -> TenantConfigSummaryResponse:
        return TenantConfigSummaryResponse(
            empresa_id=empresa_id,
            scope=scope,
            total_count=int(summary.get("total_count", 0)),
            active_count=int(summary.get("active_count", 0)),
            inactive_count=int(summary.get("inactive_count", 0)),
            pending_count=int(summary.get("pending_count", 0)),
            ok_count=int(summary.get("ok_count", 0)),
            failed_count=int(summary.get("failed_count", 0)),
            retrying_count=int(summary.get("retrying_count", 0)),
            dead_letter_count=int(summary.get("dead_letter_count", 0)),
            connector_types=[str(item) for item in summary.get("connector_types", [])],
        )

    def get_source_summary(self, empresa_id: str) -> TenantConfigSummaryResponse:
        self._ensure_tenant_exists(empresa_id)
        summary = self.source_repository.summary_by_empresa_id(empresa_id)
        return self._to_summary(empresa_id, "source", summary)

    def get_destination_summary(self, empresa_id: str) -> TenantConfigSummaryResponse:
        self._ensure_tenant_exists(empresa_id)
        summary = self.destination_repository.summary_by_empresa_id(empresa_id)
        return self._to_summary(empresa_id, "destination", summary)

    def create_source_config(
        self, empresa_id: str, payload: TenantConfigCreateRequest
    ) -> TenantConfigResponse:
        self._ensure_tenant_exists(empresa_id)
        self._ensure_connector_supported(payload.connector_type, "source")
        config = self.source_repository.create(
            config_id=str(uuid4()),
            empresa_id=empresa_id,
            nome=payload.nome,
            connector_type=payload.connector_type,
            sync_interval_minutes=payload.sync_interval_minutes,
            settings_json=self._to_json(payload.settings),
        )
        return self._to_response(config, empresa_id)

    def create_destination_config(
        self, empresa_id: str, payload: TenantConfigCreateRequest
    ) -> TenantConfigResponse:
        self._ensure_tenant_exists(empresa_id)
        self._ensure_connector_supported(payload.connector_type, "destination")
        config = self.destination_repository.create(
            config_id=str(uuid4()),
            empresa_id=empresa_id,
            nome=payload.nome,
            connector_type=payload.connector_type,
            sync_interval_minutes=payload.sync_interval_minutes,
            settings_json=self._to_json(payload.settings),
        )
        return self._to_response(config, empresa_id)

    def update_source_config(
        self, empresa_id: str, config_id: str, payload: TenantConfigUpdateRequest
    ) -> TenantConfigResponse:
        self._ensure_tenant_exists(empresa_id)
        if payload.connector_type:
            self._ensure_connector_supported(payload.connector_type, "source")
        config = self.source_repository.get_by_id(empresa_id, config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao nao encontrada.",
            )
        updated = self.source_repository.update(
            config,
            nome=payload.nome,
            connector_type=payload.connector_type,
            sync_interval_minutes=payload.sync_interval_minutes,
            settings_json=self._to_json(payload.settings) if payload.settings is not None else None,
            ativo=payload.ativo,
        )
        return self._to_response(updated, empresa_id)

    def update_destination_config(
        self, empresa_id: str, config_id: str, payload: TenantConfigUpdateRequest
    ) -> TenantConfigResponse:
        self._ensure_tenant_exists(empresa_id)
        if payload.connector_type:
            self._ensure_connector_supported(payload.connector_type, "destination")
        config = self.destination_repository.get_by_id(empresa_id, config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao nao encontrada.",
            )
        updated = self.destination_repository.update(
            config,
            nome=payload.nome,
            connector_type=payload.connector_type,
            sync_interval_minutes=payload.sync_interval_minutes,
            settings_json=self._to_json(payload.settings) if payload.settings is not None else None,
            ativo=payload.ativo,
        )
        return self._to_response(updated, empresa_id)

    def delete_source_config(self, empresa_id: str, config_id: str) -> TenantConfigDeleteResponse:
        self._ensure_tenant_exists(empresa_id)
        config = self.source_repository.get_by_id(empresa_id, config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao nao encontrada.",
            )
        self.source_repository.delete(config)
        return TenantConfigDeleteResponse(id=config_id, empresa_id=empresa_id, status="deleted")

    def delete_destination_config(
        self, empresa_id: str, config_id: str
    ) -> TenantConfigDeleteResponse:
        self._ensure_tenant_exists(empresa_id)
        config = self.destination_repository.get_by_id(empresa_id, config_id)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuracao nao encontrada.",
            )
        self.destination_repository.delete(config)
        return TenantConfigDeleteResponse(id=config_id, empresa_id=empresa_id, status="deleted")

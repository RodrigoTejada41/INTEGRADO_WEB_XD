from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.repositories.venda_repository import VendaRepository
from backend.connectors.discovery import discover_connector_classes
from backend.utils.settings_resolver import resolve_runtime_settings


@dataclass(frozen=True)
class DestinationDeliveryResult:
    delivered_count: int
    connector_type: str


class DestinationConnector:
    connector_type: str

    def deliver_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        records: list[dict],
    ) -> DestinationDeliveryResult:
        raise NotImplementedError


class PostgreSQLDestinationConnector(DestinationConnector):
    connector_type = "postgresql"

    def deliver_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        records: list[dict],
    ) -> DestinationDeliveryResult:
        settings = resolve_runtime_settings(settings)
        destination_url = (
            settings.get("database_url")
            or settings.get("postgresql_url")
            or settings.get("destination_url")
        )
        if not destination_url:
            raise RuntimeError("database_url nao informado nas configuracoes do destino")

        engine = create_engine(destination_url, pool_pre_ping=True, future=True)
        session_factory = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)
        with session_factory() as session:
            repository = VendaRepository(session)
            repository.bulk_upsert(empresa_id=empresa_id, records=records)
            session.commit()

        return DestinationDeliveryResult(delivered_count=len(records), connector_type=self.connector_type)


class DestinationConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, DestinationConnector] = {}

    def register(self, connector: DestinationConnector) -> None:
        self._connectors[connector.connector_type] = connector

    def get(self, connector_type: str) -> DestinationConnector:
        connector = self._connectors.get(connector_type)
        if connector is None:
            raise RuntimeError(f"connector_type nao suportado: {connector_type}")
        return connector


def get_default_destination_connector_registry() -> DestinationConnectorRegistry:
    registry = DestinationConnectorRegistry()
    for connector_class in discover_connector_classes("backend.connectors", DestinationConnector):
        registry.register(connector_class())
    return registry

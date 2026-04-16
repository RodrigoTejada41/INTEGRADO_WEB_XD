from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConnectorDefinition:
    name: str
    direction: str
    description: str


class ConnectorRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ConnectorDefinition] = {}

    def register(self, definition: ConnectorDefinition) -> None:
        self._definitions[definition.name] = definition

    def is_supported(self, connector_type: str) -> bool:
        return connector_type in self._definitions

    def get(self, connector_type: str) -> ConnectorDefinition | None:
        return self._definitions.get(connector_type)

    def list(self) -> list[ConnectorDefinition]:
        return sorted(self._definitions.values(), key=lambda item: item.name)


def get_default_connector_registry() -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register(
        ConnectorDefinition(
            name="mariadb",
            direction="source",
            description="Origem MariaDB para captura incremental.",
        )
    )
    registry.register(
        ConnectorDefinition(
            name="postgresql",
            direction="destination",
            description="Destino PostgreSQL para carga central.",
        )
    )
    registry.register(
        ConnectorDefinition(
            name="api",
            direction="source",
            description="Origem baseada em API externa.",
        )
    )
    registry.register(
        ConnectorDefinition(
            name="file",
            direction="source",
            description="Origem baseada em arquivo.",
        )
    )
    return registry

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

    def is_supported_for(self, direction: str, connector_type: str) -> bool:
        definition = self._definitions.get(connector_type)
        return definition is not None and definition.direction == direction

    def list_by_direction(self, direction: str) -> list[ConnectorDefinition]:
        return sorted(
            (definition for definition in self._definitions.values() if definition.direction == direction),
            key=lambda item: item.name,
        )

    def source_types(self) -> list[str]:
        return [definition.name for definition in self.list_by_direction("source")]

    def destination_types(self) -> list[str]:
        return [definition.name for definition in self.list_by_direction("destination")]

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

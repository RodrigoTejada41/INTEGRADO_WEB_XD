from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
from uuid import uuid4

from backend.connectors.discovery import discover_connector_classes
from backend.connectors.registry import get_default_connector_registry
from backend.connectors.destination_connectors import DestinationConnector
from backend.connectors.source_connectors import FileSourceConnector, SourceConnector, get_default_source_connector_registry


def test_source_connector_registry_and_file_connector() -> None:
    registry = get_default_source_connector_registry()
    assert registry.get("mariadb").connector_type == "mariadb"
    assert registry.get("api").connector_type == "api"
    assert registry.get("file").connector_type == "file"

    connector_registry = get_default_connector_registry()
    assert connector_registry.is_supported_for("source", "mariadb")
    assert connector_registry.is_supported_for("destination", "postgresql")
    assert not connector_registry.is_supported_for("source", "postgresql")
    assert not connector_registry.is_supported_for("destination", "mariadb")
    assert connector_registry.source_types() == ["api", "file", "mariadb"]
    assert connector_registry.destination_types() == ["postgresql"]

    file_path = Path("output/test_source_records.json")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(
            [
                {
                    "uuid": "11111111-1111-1111-1111-111111111111",
                    "empresa_id": "12345678000199",
                    "produto": "Produto arquivo",
                    "valor": "42.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T10:00:00+00:00",
                },
                {
                    "uuid": "22222222-2222-2222-2222-222222222222",
                    "empresa_id": "99999999000199",
                    "produto": "Outra empresa",
                    "valor": "99.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T11:00:00+00:00",
                },
            ]
        ),
        encoding="utf-8",
    )

    connector = FileSourceConnector()
    result = connector.fetch_records(
        settings={"path": str(file_path)},
        empresa_id="12345678000199",
        since=datetime(2026, 4, 15, tzinfo=UTC),
        limit=10,
    )

    assert result.connector_type == "file"
    assert len(result.records) == 1
    assert result.records[0]["produto"] == "Produto arquivo"


def test_file_source_connector_resolves_settings_from_file_reference() -> None:
    records_path = Path("output/test_source_records_ref.json")
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(
        json.dumps(
            [
                {
                    "uuid": "33333333-3333-3333-3333-333333333333",
                    "empresa_id": "12345678000199",
                    "produto": "Produto via referencia",
                    "valor": "55.00",
                    "data": "2026-04-16",
                    "data_atualizacao": "2026-04-16T12:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )

    settings_path = Path("output/test_source_settings_ref.json")
    settings_path.write_text(
        json.dumps(
            {
                "tenant_a": {
                    "path": str(records_path),
                }
            }
        ),
        encoding="utf-8",
    )

    connector = FileSourceConnector()
    result = connector.fetch_records(
        settings={
            "settings_file": str(settings_path),
            "settings_key": "tenant_a",
        },
        empresa_id="12345678000199",
        since=datetime(2026, 4, 15, tzinfo=UTC),
        limit=10,
    )

    assert result.connector_type == "file"
    assert len(result.records) == 1
    assert result.records[0]["produto"] == "Produto via referencia"


def test_connector_discovery_loads_plugins_from_package(monkeypatch) -> None:
    package_dir = Path("output") / f"sample_plugins_{uuid4().hex}"
    package_dir.mkdir()
    try:
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "custom_source.py").write_text(
            """
from backend.connectors.source_connectors import SourceConnector, SourceFetchResult


class CustomSourceConnector(SourceConnector):
    connector_type = "custom_source"

    def fetch_records(self, settings, empresa_id, since, limit):
        return SourceFetchResult(records=[{"uuid": "1", "produto": "Plugin", "valor": "1.00", "data": "2026-04-16", "data_atualizacao": since}], connector_type=self.connector_type)
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (package_dir / "custom_destination.py").write_text(
            """
from backend.connectors.destination_connectors import DestinationConnector, DestinationDeliveryResult


class CustomDestinationConnector(DestinationConnector):
    connector_type = "custom_destination"

    def deliver_records(self, settings, empresa_id, records):
        return DestinationDeliveryResult(delivered_count=len(records), connector_type=self.connector_type)
""".strip()
            + "\n",
            encoding="utf-8",
        )

        monkeypatch.syspath_prepend(str(Path("output").resolve()))

        source_plugins = discover_connector_classes(package_dir.name, SourceConnector)
        destination_plugins = discover_connector_classes(package_dir.name, DestinationConnector)

        assert [plugin.connector_type for plugin in source_plugins] == ["custom_source"]
        assert [plugin.connector_type for plugin in destination_plugins] == ["custom_destination"]
    finally:
        shutil.rmtree(package_dir, ignore_errors=True)

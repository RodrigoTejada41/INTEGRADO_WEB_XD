from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from backend.connectors.source_connectors import FileSourceConnector, get_default_source_connector_registry


def test_source_connector_registry_and_file_connector() -> None:
    registry = get_default_source_connector_registry()
    assert registry.get("mariadb").connector_type == "mariadb"
    assert registry.get("api").connector_type == "api"
    assert registry.get("file").connector_type == "file"

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

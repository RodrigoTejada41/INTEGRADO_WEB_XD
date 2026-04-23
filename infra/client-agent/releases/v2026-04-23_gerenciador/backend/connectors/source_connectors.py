from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
import csv
import json

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.connectors.discovery import discover_connector_classes
from backend.utils.settings_resolver import resolve_runtime_settings


@dataclass(frozen=True)
class SourceFetchResult:
    records: list[dict]
    connector_type: str


class SourceConnector:
    connector_type: str

    def fetch_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> SourceFetchResult:
        raise NotImplementedError


class MariaDBSourceConnector(SourceConnector):
    connector_type = "mariadb"

    def fetch_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> SourceFetchResult:
        settings = resolve_runtime_settings(settings)
        source_url = settings.get("mariadb_url") or settings.get("database_url")
        if not source_url:
            raise RuntimeError("mariadb_url nao informado nas configuracoes da origem")

        source_query = settings.get("source_query")
        if source_query:
            stmt = text(source_query)
            params = {"empresa_id": empresa_id, "since": since, "limit": limit}
        else:
            stmt = text(
                """
                SELECT
                    uuid,
                    empresa_id,
                    produto,
                    valor,
                    data,
                    data_atualizacao
                FROM vendas
                WHERE empresa_id = :empresa_id
                  AND data_atualizacao > :since
                ORDER BY data_atualizacao ASC
                LIMIT :limit
                """
            )
            params = {"empresa_id": empresa_id, "since": since, "limit": limit}

        engine = create_engine(source_url, pool_pre_ping=True, future=True)
        session_factory = sessionmaker(bind=engine, class_=Session, autoflush=False)
        with session_factory() as session:
            rows = session.execute(stmt, params).mappings().all()

        records: list[dict] = []
        for row in rows:
            data_atualizacao = row["data_atualizacao"]
            if isinstance(data_atualizacao, str):
                data_atualizacao = datetime.fromisoformat(data_atualizacao)
            if data_atualizacao.tzinfo is None:
                data_atualizacao = data_atualizacao.replace(tzinfo=UTC)
            data_value = row["data"]
            if isinstance(data_value, str):
                data_value = date.fromisoformat(data_value)
            records.append(
                {
                    "uuid": str(row["uuid"]),
                    "produto": str(row["produto"]),
                    "valor": str(row["valor"]),
                    "data": data_value,
                    "data_atualizacao": data_atualizacao,
                }
            )
        return SourceFetchResult(records=records, connector_type=self.connector_type)


class ApiSourceConnector(SourceConnector):
    connector_type = "api"

    def fetch_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> SourceFetchResult:
        settings = resolve_runtime_settings(settings)
        base_url = settings.get("base_url")
        endpoint = settings.get("endpoint", "/records")
        if not base_url:
            raise RuntimeError("base_url nao informado nas configuracoes da origem")

        headers = {"Content-Type": "application/json"}
        api_key = settings.get("api_key")
        if api_key:
            headers["X-API-Key"] = api_key

        timeout_seconds = int(settings.get("timeout_seconds", "30"))
        with httpx.Client(timeout=timeout_seconds, verify=settings.get("verify_ssl", "true") == "true") as client:
            response = client.get(
                f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}",
                headers=headers,
                params={
                    "empresa_id": empresa_id,
                    "since": since.isoformat(),
                    "limit": limit,
                },
            )
            response.raise_for_status()
            body = response.json()

        if isinstance(body, dict):
            records = body.get("records", [])
        else:
            records = body
        return SourceFetchResult(records=list(records), connector_type=self.connector_type)


class FileSourceConnector(SourceConnector):
    connector_type = "file"

    def fetch_records(
        self,
        settings: dict[str, str],
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> SourceFetchResult:
        settings = resolve_runtime_settings(settings)
        file_path = settings.get("path")
        if not file_path:
            raise RuntimeError("path nao informado nas configuracoes da origem")

        path = Path(file_path)
        if not path.exists():
            raise RuntimeError(f"arquivo de origem inexistente: {path}")

        suffix = path.suffix.lower()
        records: list[dict] = []
        if suffix == ".csv":
            with path.open("r", encoding="utf-8", newline="") as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    if row.get("empresa_id") != empresa_id:
                        continue
                    records.append(row)
                    if len(records) >= limit:
                        break
        else:
            with path.open("r", encoding="utf-8") as fp:
                raw = fp.read().strip()
            if not raw:
                records = []
            elif raw.startswith("["):
                records = json.loads(raw)
            else:
                for line in raw.splitlines():
                    if not line.strip():
                        continue
                    records.append(json.loads(line))
                    if len(records) >= limit:
                        break

        filtered: list[dict] = []
        for record in records:
            if str(record.get("empresa_id")) != empresa_id:
                continue
            data_atualizacao = record.get("data_atualizacao")
            if data_atualizacao:
                parsed = datetime.fromisoformat(str(data_atualizacao))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                if parsed <= since:
                    continue
                record["data_atualizacao"] = parsed
            data_value = record.get("data")
            if isinstance(data_value, str):
                try:
                    record["data"] = date.fromisoformat(data_value)
                except ValueError:
                    pass
            filtered.append(record)
        return SourceFetchResult(records=filtered[:limit], connector_type=self.connector_type)


class SourceConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector) -> None:
        self._connectors[connector.connector_type] = connector

    def get(self, connector_type: str) -> SourceConnector:
        connector = self._connectors.get(connector_type)
        if connector is None:
            raise RuntimeError(f"connector_type nao suportado: {connector_type}")
        return connector


def get_default_source_connector_registry() -> SourceConnectorRegistry:
    registry = SourceConnectorRegistry()
    for connector_class in discover_connector_classes("backend.connectors", SourceConnector):
        registry.register(connector_class())
    return registry

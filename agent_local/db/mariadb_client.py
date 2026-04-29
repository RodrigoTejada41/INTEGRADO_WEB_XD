from datetime import datetime
import json

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from agent_local.db.xd_sales_mapper import (
    AUTO_SOURCE_QUERY,
    build_xd_salesdocuments_query,
    canonicalize_sales_row,
)


class MariaDBClient:
    def __init__(self, mariadb_url: str, source_query: str | None = None):
        self.engine = create_engine(mariadb_url, pool_pre_ping=True, future=True)
        self.session_factory = sessionmaker(bind=self.engine, class_=Session, autoflush=False)
        self.source_query = source_query

    def fetch_changed_vendas(
        self,
        empresa_id: str,
        since: datetime,
        limit: int,
    ) -> list[dict]:
        if self.source_query:
            source_query = self._resolve_source_query()
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

        with self.session_factory() as session:
            if self.source_query and self.source_query.strip().lower() == AUTO_SOURCE_QUERY:
                stmt = text(self._discover_source_query(session))
            rows = session.execute(stmt, params).mappings()
            items = []
            for row in rows:
                items.append(canonicalize_sales_row(row))
            return items

    def ping(self) -> bool:
        stmt = text("SELECT 1")
        with self.session_factory() as session:
            session.execute(stmt)
        return True

    def fetch_source_metadata(self, empresa_id: str) -> dict[str, object]:
        with self.session_factory() as session:
            tables = self._list_tables(session)
            metadata: dict[str, object] = {
                "cnpj": empresa_id,
                "company_name": self._discover_company_name(session, tables),
                "payment_methods": self._discover_payment_methods(session, tables),
            }
            return {key: value for key, value in metadata.items() if value}

    def _resolve_source_query(self) -> str:
        if not self.source_query:
            raise RuntimeError("source_query nao configurada.")
        if self.source_query.strip().lower() == AUTO_SOURCE_QUERY:
            return self.source_query
        return self.source_query

    def _discover_source_query(self, session: Session) -> str:
        tables = self._list_tables(session)
        table_columns = self._list_columns_for_reference_tables(session, tables)
        sales_view = self._find_table(tables, "salesdocumentsreportview")
        columns = self._list_columns(session, sales_view) if sales_view else set()
        return build_xd_salesdocuments_query(
            columns=columns,
            tables=tables,
            table_columns=table_columns,
        )

    def inspect_xd_mapping(self) -> dict[str, object]:
        with self.session_factory() as session:
            tables = self._list_tables(session)
            table_columns = self._list_columns_for_reference_tables(session, tables)
            has_sales_view = self._find_table(tables, "salesdocumentsreportview") is not None
            has_documents_fallback = (
                self._find_table(tables, "documentsbodys") is not None
                and self._find_table(tables, "documentsheaders") is not None
            )
            source_kind = "salesdocumentsreportview" if has_sales_view else "documentsbodys_documentsheaders"
            try:
                self._discover_source_query(session)
                status = "ok"
                error = ""
            except Exception as exc:
                status = "error"
                error = str(exc)
            return {
                "status": status,
                "source_kind": source_kind,
                "error": error,
                "tables_present": sorted(tables),
                "has_salesdocumentsreportview": has_sales_view,
                "has_documents_fallback": has_documents_fallback,
                "reference_tables": {
                    table: sorted(columns)
                    for table, columns in sorted(table_columns.items(), key=lambda item: item[0].lower())
                },
            }

    def _list_tables(self, session: Session) -> set[str]:
        rows = session.execute(text("SHOW FULL TABLES")).fetchall()
        return {str(row[0]) for row in rows}

    def _list_columns(self, session: Session, table_name: str) -> set[str]:
        safe_table_name = table_name.replace("`", "")
        rows = session.execute(text(f"SHOW COLUMNS FROM `{safe_table_name}`")).fetchall()
        return {str(row[0]) for row in rows}

    def _list_columns_for_reference_tables(self, session: Session, tables: set[str]) -> dict[str, set[str]]:
        reference_names = {
            "salesdocumentsreportview",
            "documentsbodys",
            "documentsheaders",
            "documentsbodysdeleted",
            "invoicepaymentdetails",
            "xconfigpaymenttypes",
            "itemsgroups",
            "items",
            "xconfigitemsunits",
            "entities",
        }
        result: dict[str, set[str]] = {}
        for reference_name in reference_names:
            table_name = self._find_table(tables, reference_name)
            if table_name:
                result[table_name] = self._list_columns(session, table_name)
        return result

    @staticmethod
    def _find_table(tables: set[str], expected_name: str) -> str | None:
        for table in tables:
            if table.lower() == expected_name.lower():
                return table
        return None

    def _discover_company_name(self, session: Session, tables: set[str]) -> str | None:
        if "xconfig" in tables:
            columns = self._list_columns(session, "xconfig")
            for column in ("AmEntrerpriseName", "AmEnterpriseName", "CompanyName"):
                if column in columns:
                    value = session.execute(text(f"SELECT `{column}` FROM xconfig LIMIT 1")).scalar()
                    if value and str(value).strip():
                        return str(value).strip()

        if "config" in tables:
            rows = session.execute(
                text("SELECT Data FROM config WHERE Id IN ('AirMenuConfig', 'EnterpriseConfig') LIMIT 5")
            ).scalars()
            for raw_value in rows:
                discovered = self._extract_company_name_from_config_json(raw_value)
                if discovered:
                    return discovered
        return None

    def _discover_payment_methods(self, session: Session, tables: set[str]) -> list[str]:
        if "xconfigpaymenttypes" not in tables:
            return []
        columns = self._list_columns(session, "xconfigpaymenttypes")
        inactive_filter = "WHERE COALESCE(Inactive, 0) = 0" if "Inactive" in columns else ""
        rows = session.execute(
            text(
                f"""
                SELECT DISTINCT Description
                FROM xconfigpaymenttypes
                {inactive_filter}
                ORDER BY Description ASC
                LIMIT 100
                """
            )
        ).scalars()
        return [str(item).strip() for item in rows if item and str(item).strip()]

    @staticmethod
    def _extract_company_name_from_config_json(raw_value: object) -> str | None:
        if not raw_value:
            return None
        try:
            payload = json.loads(str(raw_value))
        except json.JSONDecodeError:
            return None
        candidates = [
            payload.get("EnterpriseName"),
            payload.get("EnterpriseId"),
        ]
        enterprise_data = payload.get("EnterpriseData")
        if isinstance(enterprise_data, dict):
            candidates.extend(
                [
                    enterprise_data.get("name"),
                    enterprise_data.get("enterpriseName"),
                    enterprise_data.get("companyName"),
                ]
            )
        for candidate in candidates:
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        return None

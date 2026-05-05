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
    def __init__(self, mariadb_url: str, source_query: str | None = None, terminal_id: int = 1):
        self.engine = create_engine(mariadb_url, pool_pre_ping=True, future=True)
        self.session_factory = sessionmaker(bind=self.engine, class_=Session, autoflush=False)
        self.source_query = source_query
        self.terminal_id = terminal_id

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
            if self._should_auto_discover_source_query():
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

    def fetch_order_catalog(self) -> dict[str, list[dict[str, str]]]:
        with self.session_factory() as session:
            tables = self._list_tables(session)
            table_columns = self._list_columns_for_reference_tables(session, tables)
            return {
                "operators": self._discover_order_operators(session, tables),
                "products": self._discover_order_products(session, tables, table_columns),
            }

    def _resolve_source_query(self) -> str:
        if not self.source_query:
            raise RuntimeError("source_query nao configurada.")
        if self._should_auto_discover_source_query():
            return self.source_query
        return self.source_query

    def _should_auto_discover_source_query(self) -> bool:
        if not self.source_query:
            return False
        normalized = " ".join(self.source_query.strip().lower().split())
        if normalized == AUTO_SOURCE_QUERY:
            return True
        return (
            "from salesdocumentsreportview" in normalized
            and "familia_produto" not in normalized
            and "codigo_produto_local" not in normalized
        )

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
            "operators",
            "employees",
            "users",
            "xconfigoperators",
            "xconfigprinters",
            "xconfig",
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

    def _discover_order_operators(self, session: Session, tables: set[str]) -> list[dict[str, str]]:
        for expected_table in ("xconfigoperators", "operators", "employees", "users"):
            table_name = self._find_table(tables, expected_table)
            if not table_name:
                continue
            columns = self._list_columns(session, table_name)
            code_column = self._first_available_column(columns, ("Code", "KeyId", "Id", "UserName", "Login", "Name"))
            name_column = self._first_available_column(columns, ("Name", "Description", "FullName", "UserName", "Login"))
            password_column = self._first_available_column(
                columns,
                ("Password", "PassWord", "Senha", "Pass", "Pwd", "UserPassword"),
            )
            if not code_column or not name_column:
                continue
            password_expr = f"`{password_column}`" if password_column else "NULL"
            inactive_filter = "WHERE COALESCE(Inactive, 0) = 0" if "Inactive" in columns else ""
            rows = session.execute(
                text(
                    f"""
                    SELECT DISTINCT
                        `{code_column}` AS code,
                        `{name_column}` AS name,
                        {password_expr} AS password
                    FROM `{table_name}`
                    {inactive_filter}
                    ORDER BY `{name_column}` ASC
                    LIMIT 100
                    """
                )
            ).mappings()
            discovered = self._normalize_operator_rows(rows)
            if discovered:
                return discovered

        header_table = self._find_table(tables, "documentsheaders")
        if not header_table:
            return []
        header_columns = self._list_columns(session, header_table)
        name_column = self._first_available_column(header_columns, ("OperatorName", "SalesmanName", "EmployeeName"))
        if not name_column:
            return []
        rows = session.execute(
            text(
                f"""
                SELECT DISTINCT `{name_column}` AS code, `{name_column}` AS name, NULL AS password
                FROM `{header_table}`
                WHERE `{name_column}` IS NOT NULL AND TRIM(`{name_column}`) <> ''
                ORDER BY `{name_column}` ASC
                LIMIT 100
                """
            )
        ).mappings()
        return self._normalize_operator_rows(rows)

    def _discover_order_products(
        self,
        session: Session,
        tables: set[str],
        table_columns: dict[str, set[str]],
    ) -> list[dict[str, str]]:
        items_table = self._find_table(tables, "items")
        if items_table:
            items_columns = self._list_columns(session, items_table)
            code_column = self._first_available_column(items_columns, ("KeyId", "ItemKeyId", "Code", "Id"))
            description_column = self._first_available_column(items_columns, ("Description", "Name"))
            price_column = self._first_available_column(
                items_columns,
                (
                    "RetailPrice1",
                    "RetailPrice",
                    "SalePrice",
                    "UnitPrice",
                    "Price",
                    "Pvp",
                    "NetPrice1",
                    "AskingPrice",
                ),
            )
            group_column = self._first_available_column(items_columns, ("GroupId", "ItemGroupId"))
            groups_table = self._find_table(tables, "itemsgroups")
            if code_column and description_column:
                family_expr = "'Geral'"
                join_sql = ""
                if groups_table and group_column:
                    groups_columns = table_columns.get(groups_table) or self._list_columns(session, groups_table)
                    group_key = self._first_available_column(groups_columns, ("Id", "KeyId", "GroupId"))
                    group_name = self._first_available_column(groups_columns, ("Description", "Name"))
                    if group_key and group_name:
                        join_sql = f"LEFT JOIN `{groups_table}` g ON g.`{group_key}` = i.`{group_column}`"
                        family_expr = f"COALESCE(g.`{group_name}`, 'Geral')"
                price_expr = f"COALESCE(i.`{price_column}`, 0)" if price_column else "0"
                inactive_filter = "WHERE COALESCE(i.Inactive, 0) = 0" if "Inactive" in items_columns else ""
                rows = session.execute(
                    text(
                        f"""
                        SELECT DISTINCT
                            i.`{code_column}` AS product_code,
                            i.`{description_column}` AS description,
                            {family_expr} AS family,
                            {price_expr} AS unit_price
                        FROM `{items_table}` i
                        {join_sql}
                        {inactive_filter}
                        ORDER BY family, description
                        LIMIT 500
                        """
                    )
                ).mappings()
                products = self._normalize_product_rows(rows)
                printer_mappings = self._discover_xd_production_printer_mappings(
                    session=session,
                    tables=tables,
                    items_table=items_table,
                    items_columns=items_columns,
                    code_column=code_column,
                    group_column=group_column,
                    groups_table=groups_table,
                    table_columns=table_columns,
                )
                for product in products:
                    mapped_printers = printer_mappings.get(product["product_code"])
                    if mapped_printers:
                        product["production_printers"] = mapped_printers
                if products:
                    return products

        sales_view = self._find_table(tables, "salesdocumentsreportview")
        if not sales_view:
            return []
        columns = self._list_columns(session, sales_view)
        if not {"ItemKeyId", "ItemDescription"} <= columns:
            return []
        family_expr = "COALESCE(ItemGroupId, 'Geral')" if "ItemGroupId" in columns else "'Geral'"
        price_column = self._first_available_column(
            columns,
            ("RetailPrice", "UnitPrice", "Price", "TotalAmount", "TotalNetAmount"),
        )
        price_expr = f"COALESCE({price_column}, 0)" if price_column else "0"
        rows = session.execute(
            text(
                f"""
                SELECT DISTINCT
                    ItemKeyId AS product_code,
                    ItemDescription AS description,
                    {family_expr} AS family,
                    {price_expr} AS unit_price
                FROM `{sales_view}`
                WHERE ItemKeyId IS NOT NULL
                  AND ItemDescription IS NOT NULL
                ORDER BY family, description
                LIMIT 500
                """
            )
        ).mappings()
        return self._normalize_product_rows(rows)

    def _discover_xd_production_printer_mappings(
        self,
        *,
        session: Session,
        tables: set[str],
        items_table: str,
        items_columns: set[str],
        code_column: str,
        group_column: str | None,
        groups_table: str | None,
        table_columns: dict[str, set[str]],
    ) -> dict[str, list[dict[str, object]]]:
        printer_slots = [index for index in range(1, 21) if f"Printer{index}" in items_columns]
        if not printer_slots:
            return {}

        printer_configs = self._discover_xd_printer_configs(session, tables, table_columns)
        if not printer_configs:
            return {}

        select_columns = [f"i.`{code_column}` AS product_code"]
        for index in printer_slots:
            select_columns.append(f"i.`Printer{index}` AS item_printer_{index}")

        group_slots: list[int] = []
        join_sql = ""
        if groups_table and group_column:
            groups_columns = table_columns.get(groups_table) or self._list_columns(session, groups_table)
            group_key = self._first_available_column(groups_columns, ("Id", "KeyId", "GroupId"))
            if group_key:
                group_slots = [index for index in range(1, 21) if f"Printer{index}" in groups_columns]
                if group_slots:
                    join_sql = f"LEFT JOIN `{groups_table}` g ON g.`{group_key}` = i.`{group_column}`"
                    for index in group_slots:
                        select_columns.append(f"g.`Printer{index}` AS group_printer_{index}")

        rows = session.execute(
            text(
                f"""
                SELECT {", ".join(select_columns)}
                FROM `{items_table}` i
                {join_sql}
                """
            )
        ).mappings()

        mappings: dict[str, list[dict[str, object]]] = {}
        for row in rows:
            product_code = str(row["product_code"]).strip() if row["product_code"] is not None else ""
            if not product_code:
                continue
            printers: list[dict[str, object]] = []
            for index in printer_slots:
                item_enabled = self._truthy(row.get(f"item_printer_{index}"))
                group_enabled = self._truthy(row.get(f"group_printer_{index}")) if index in group_slots else False
                if not item_enabled and not group_enabled:
                    continue
                config = printer_configs.get(index)
                if config:
                    printers.append(config)
            if printers:
                mappings[product_code] = printers
        return mappings

    def _discover_xd_printer_configs(
        self,
        session: Session,
        tables: set[str],
        table_columns: dict[str, set[str]],
    ) -> dict[int, dict[str, object]]:
        printers_table = self._find_table(tables, "xconfigprinters")
        if not printers_table:
            return {}
        columns = table_columns.get(printers_table) or self._list_columns(session, printers_table)
        if not {"Port", "ReportConfiguration"} <= columns:
            return {}

        terminal_filter = ""
        params: dict[str, object] = {}
        if "Terminal" in columns:
            terminal_filter = "WHERE Terminal = :terminal_id"
            params["terminal_id"] = self.terminal_id
        if "UsePrinter" in columns:
            terminal_filter += " AND COALESCE(UsePrinter, 0) = 1" if terminal_filter else "WHERE COALESCE(UsePrinter, 0) = 1"

        copies_expr = "NumberCopies" if "NumberCopies" in columns else "1 AS NumberCopies"
        terminal_expr = "Terminal" if "Terminal" in columns else f"{int(self.terminal_id)} AS Terminal"
        rows = session.execute(
            text(
                f"""
                SELECT Id, Port, ReportConfiguration, {terminal_expr}, {copies_expr}
                FROM `{printers_table}`
                {terminal_filter}
                ORDER BY Id ASC
                LIMIT 20
                """
            ),
            params,
        ).mappings()
        labels = self._discover_xd_printer_labels(session, tables, table_columns)
        configs: dict[int, dict[str, object]] = {}
        for slot, row in enumerate(rows, start=1):
            port = str(row["Port"]).strip() if row["Port"] is not None else ""
            if not port:
                continue
            configs[slot] = {
                "slot": slot,
                "printer_id": int(row["Id"]),
                "terminal_id": int(row["Terminal"] or self.terminal_id),
                "copies": int(row["NumberCopies"] or 1),
                "label": labels.get(slot) or f"Imp.Producao{slot}",
                "printer_name": port,
                "report": str(row["ReportConfiguration"] or "").strip(),
            }
        return configs

    def _discover_xd_printer_labels(
        self,
        session: Session,
        tables: set[str],
        table_columns: dict[str, set[str]],
    ) -> dict[int, str]:
        config_table = self._find_table(tables, "xconfig")
        if not config_table:
            return {}
        columns = table_columns.get(config_table) or self._list_columns(session, config_table)
        printer_columns = [f"Printer{index}" for index in range(1, 21) if f"Printer{index}" in columns]
        if not printer_columns:
            return {}
        row = session.execute(
            text(f"SELECT {', '.join(f'`{column}`' for column in printer_columns)} FROM `{config_table}` LIMIT 1")
        ).mappings().first()
        if row is None:
            return {}
        labels: dict[int, str] = {}
        for column in printer_columns:
            value = row.get(column)
            if value and str(value).strip():
                labels[int(column.replace("Printer", ""))] = str(value).strip()
        return labels

    @staticmethod
    def _truthy(value: object) -> bool:
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "sim", "s"}

    @staticmethod
    def _first_available_column(columns: set[str], candidates: tuple[str, ...]) -> str | None:
        lowered = {column.lower(): column for column in columns}
        for candidate in candidates:
            found = lowered.get(candidate.lower())
            if found:
                return found
        return None

    @staticmethod
    def _normalize_operator_rows(rows) -> list[dict[str, str]]:
        operators = []
        seen = set()
        for row in rows:
            code = str(row["code"]).strip() if row["code"] is not None else ""
            name = str(row["name"]).strip() if row["name"] is not None else ""
            if not code or not name or code in seen:
                continue
            seen.add(code)
            operator = {"code": code, "name": name}
            password = row.get("password") if hasattr(row, "get") else None
            if password is not None and str(password).strip():
                operator["password"] = str(password).strip()
            operators.append(operator)
        return operators

    @staticmethod
    def _normalize_product_rows(rows) -> list[dict[str, str]]:
        products = []
        seen = set()
        for row in rows:
            product_code = str(row["product_code"]).strip() if row["product_code"] is not None else ""
            description = str(row["description"]).strip() if row["description"] is not None else ""
            family = str(row["family"]).strip() if row["family"] is not None else "Geral"
            unit_price = str(row["unit_price"]).strip() if row["unit_price"] is not None else "0"
            if not product_code or not description or product_code in seen:
                continue
            seen.add(product_code)
            products.append(
                {
                    "product_code": product_code,
                    "description": description,
                    "family": family or "Geral",
                    "unit_price": unit_price or "0",
                }
            )
        return products

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

from __future__ import annotations

from datetime import UTC
from typing import Mapping


AUTO_SOURCE_QUERY = "auto"

OPTIONAL_CANONICAL_FIELDS = (
    "branch_code",
    "terminal_code",
    "tipo_venda",
    "forma_pagamento",
    "bandeira_cartao",
    "familia_produto",
    "categoria_produto",
    "codigo_produto_local",
    "unidade",
    "operador",
    "cliente",
    "status_venda",
    "cancelada",
    "quantidade",
    "valor_unitario",
    "valor_bruto",
    "desconto",
    "acrescimo",
    "valor_liquido",
)


def canonicalize_sales_row(row: Mapping[str, object]) -> dict[str, object]:
    data_atualizacao = row["data_atualizacao"]
    if getattr(data_atualizacao, "tzinfo", None) is None:
        data_atualizacao = data_atualizacao.replace(tzinfo=UTC)

    item: dict[str, object] = {
        "uuid": str(row["uuid"]),
        "empresa_id": str(row["empresa_id"]),
        "produto": row["produto"],
        "valor": str(row["valor"]),
        "data": row["data"].isoformat(),
        "data_atualizacao": data_atualizacao.isoformat(),
    }

    for field in OPTIONAL_CANONICAL_FIELDS:
        value = row.get(field)
        if value is not None and str(value).strip():
            item[field] = value if isinstance(value, bool) else str(value).strip()

    return item


def build_xd_salesdocuments_query(
    columns: set[str],
    tables: set[str],
    table_columns: Mapping[str, set[str]] | None = None,
) -> str:
    if "salesdocumentsreportview" not in {table.lower() for table in tables}:
        if table_columns is None:
            raise RuntimeError("Auto-mapeamento requer salesdocumentsreportview ou Documentsbodys/Documentsheaders.")
        return build_xd_documents_query(tables=tables, table_columns=table_columns)

    required_columns = {
        "DocumentKeyId",
        "ItemKeyId",
        "CloseDate",
        "CreationDate",
        "ItemDescription",
        "TotalAmount",
    }
    missing = required_columns - columns
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(f"salesdocumentsreportview sem colunas obrigatorias: {missing_list}")

    tables_lower = {table.lower() for table in tables}
    optional_selects = [
        _literal("'0001'", "branch_code"),
        _column("v", "Terminal", "terminal_code", columns),
        _column("v", "DocumentDescription", "tipo_venda", columns),
        _column("v", "ItemKeyId", "codigo_produto_local", columns),
        _column("v", "Quantity", "quantidade", columns),
        _column("v", "UnitPrice", "valor_unitario", columns),
        _column("v", "GrossAmount", "valor_bruto", columns),
        _column("v", "DiscountAmount", "desconto", columns),
        _column("v", "OtherCostsAmount", "acrescimo", columns),
        _column("v", "TotalAmount", "valor_liquido", columns),
        _literal("'finalizada'", "status_venda"),
        _literal("0", "cancelada"),
    ]

    family_expr = _sales_view_family_expression(columns, tables_lower, table_columns)
    if family_expr:
        optional_selects.append(family_expr)
    elif "ItemGroupId" in columns:
        optional_selects.append(_column("v", "ItemGroupId", "familia_produto", columns))
    else:
        optional_selects.append(_literal("NULL", "familia_produto"))

    optional_selects.append(_literal("NULL", "categoria_produto"))
    optional_selects.append(_literal("NULL", "unidade"))
    optional_selects.append(_literal("NULL", "operador"))
    optional_selects.append(_literal("NULL", "cliente"))

    if {"invoicepaymentdetails", "xconfigpaymenttypes"} <= tables_lower and {"Number", "SerieId"} <= columns:
        optional_selects.append(
            "(\n"
            "                        SELECT GROUP_CONCAT(DISTINCT xpt.Description ORDER BY xpt.Description SEPARATOR ', ')\n"
            "                        FROM invoicepaymentdetails ipd\n"
            "                        INNER JOIN xconfigpaymenttypes xpt ON xpt.Id = ipd.PaymentTypeId\n"
            "                        WHERE ipd.InvoiceNumber = v.Number\n"
            "                          AND ipd.SerieId = v.SerieId\n"
            "                    ) AS forma_pagamento"
        )
    else:
        optional_selects.append(_literal("NULL", "forma_pagamento"))

    optional_sql = ",\n                    ".join(optional_selects)
    return f"""
                SELECT
                    SHA2(
                        CONCAT(
                            IFNULL(v.DocumentKeyId, ''),
                            '|',
                            IFNULL(v.ItemKeyId, ''),
                            '|',
                            DATE_FORMAT(COALESCE(v.CloseDate, v.CreationDate), '%Y-%m-%d %H:%i:%s')
                        ),
                        256
                    ) AS uuid,
                    :empresa_id AS empresa_id,
                    COALESCE(v.ItemDescription, 'SEM_DESCRICAO') AS produto,
                    COALESCE(v.TotalAmount, 0) AS valor,
                    DATE(COALESCE(v.CloseDate, v.CreationDate)) AS data,
                    COALESCE(v.CloseDate, v.CreationDate) AS data_atualizacao,
                    {optional_sql}
                FROM salesdocumentsreportview v
                WHERE COALESCE(v.CloseDate, v.CreationDate) > :since
                ORDER BY COALESCE(v.CloseDate, v.CreationDate) ASC
                LIMIT :limit
                """


def build_xd_documents_query(*, tables: set[str], table_columns: Mapping[str, set[str]]) -> str:
    tables_lower = {table.lower() for table in tables}
    if not {"documentsbodys", "documentsheaders"} <= tables_lower:
        raise RuntimeError("Auto-mapeamento por tabelas requer Documentsbodys e Documentsheaders.")

    body_columns = _columns_for(table_columns, "documentsbodys")
    header_columns = _columns_for(table_columns, "documentsheaders")
    required_body = {"Guid", "ItemKeyId", "ItemDescription"}
    required_header = {"SerieId", "Number"}
    missing = (required_body - body_columns) | (required_header - header_columns)
    if missing:
        raise RuntimeError(f"Documentsbodys/Documentsheaders sem colunas obrigatorias: {', '.join(sorted(missing))}")

    body_date = _coalesce_columns("b", ("CloseDate", "CreationDate", "TaxPointDate"), body_columns)
    header_date = _coalesce_columns("h", ("CloseDate", "CreationDate", "TaxPointDate"), header_columns)
    event_date = body_date if body_date != "NULL" else header_date
    if event_date == "NULL":
        raise RuntimeError("Documentsbodys/Documentsheaders sem coluna de data utilizavel.")

    value_expr = _first_existing_column("b", ("TotalAmount", "NetTotal", "TotalNetAmount", "Price"), body_columns, "0")
    gross_expr = _first_existing_column("b", ("GrossAmount", "TotalGrossAmount", "TotalAmount"), body_columns, value_expr)
    discount_expr = _first_existing_column("b", ("DiscountAmount", "DiscountValue", "Discount"), body_columns, "0")
    surcharge_expr = _first_existing_column("b", ("OtherCostsAmount", "SurchargeAmount", "ChargesAmount"), body_columns, "0")
    quantity_expr = _first_existing_column("b", ("Quantity", "Qty"), body_columns, "1")
    unit_expr = _first_existing_column("b", ("UnitPrice", "Price"), body_columns, "NULL")
    terminal_expr = _first_existing_column("b", ("Terminal",), body_columns, _first_existing_column("h", ("Terminal",), header_columns, "NULL"))
    branch_expr = _first_existing_column("h", ("SerieId",), header_columns, "'0001'")
    customer_expr = _first_existing_column("h", ("EntityName", "EntityDescription", "EntityKeyId"), header_columns, "NULL")
    status_expr = _literal("'finalizada'", "status_venda")

    family_expr = _documents_family_expression(body_columns, tables_lower, table_columns)

    payment_expr = _literal("NULL", "forma_pagamento")
    if {"invoicepaymentdetails", "xconfigpaymenttypes"} <= tables_lower:
        payment_expr = (
            "(\n"
            "                        SELECT GROUP_CONCAT(DISTINCT xpt.Description ORDER BY xpt.Description SEPARATOR ', ')\n"
            "                        FROM invoicepaymentdetails ipd\n"
            "                        INNER JOIN xconfigpaymenttypes xpt ON xpt.Id = ipd.PaymentTypeId\n"
            "                        WHERE ipd.InvoiceNumber = h.Number\n"
            "                          AND ipd.SerieId = h.SerieId\n"
            "                    ) AS forma_pagamento"
        )

    return f"""
                SELECT
                    SHA2(
                        CONCAT(
                            IFNULL(b.Guid, ''),
                            '|',
                            IFNULL(h.SerieId, ''),
                            '|',
                            IFNULL(h.Number, ''),
                            '|',
                            DATE_FORMAT({event_date}, '%Y-%m-%d %H:%i:%s')
                        ),
                        256
                    ) AS uuid,
                    :empresa_id AS empresa_id,
                    COALESCE(b.ItemDescription, 'SEM_DESCRICAO') AS produto,
                    COALESCE({value_expr}, 0) AS valor,
                    DATE({event_date}) AS data,
                    {event_date} AS data_atualizacao,
                    {branch_expr} AS branch_code,
                    {terminal_expr} AS terminal_code,
                    {_first_existing_column('h', ('DocumentDescription', 'DocumentType', 'DocumentTypeId'), header_columns, 'NULL')} AS tipo_venda,
                    {payment_expr},
                    NULL AS bandeira_cartao,
                    {family_expr},
                    NULL AS categoria_produto,
                    b.ItemKeyId AS codigo_produto_local,
                    {_first_existing_column('b', ('Unit', 'UnitDescription'), body_columns, 'NULL')} AS unidade,
                    {_first_existing_column('h', ('OperatorName', 'SalesmanName', 'EmployeeName'), header_columns, 'NULL')} AS operador,
                    {customer_expr} AS cliente,
                    {status_expr},
                    0 AS cancelada,
                    COALESCE({quantity_expr}, 1) AS quantidade,
                    {unit_expr} AS valor_unitario,
                    COALESCE({gross_expr}, {value_expr}, 0) AS valor_bruto,
                    COALESCE({discount_expr}, 0) AS desconto,
                    COALESCE({surcharge_expr}, 0) AS acrescimo,
                    COALESCE({value_expr}, 0) AS valor_liquido
                FROM Documentsbodys b
                INNER JOIN Documentsheaders h
                    ON h.SerieId = b.SerieId
                   AND h.Number = b.Number
                WHERE {event_date} > :since
                ORDER BY {event_date} ASC
                LIMIT :limit
                """


def _column(alias: str, column: str, output: str, columns: set[str]) -> str:
    if column not in columns:
        return _literal("NULL", output)
    return f"{alias}.{column} AS {output}"


def _literal(value: str, output: str) -> str:
    return f"{value} AS {output}"


def _columns_for(table_columns: Mapping[str, set[str]], table_name: str) -> set[str]:
    for key, value in table_columns.items():
        if key.lower() == table_name.lower():
            return value
    return set()


def _first_existing_column(alias: str, candidates: tuple[str, ...], columns: set[str], fallback: str) -> str:
    for column in candidates:
        if column in columns:
            return f"{alias}.{column}"
    return fallback


def _coalesce_columns(alias: str, candidates: tuple[str, ...], columns: set[str]) -> str:
    available = [f"{alias}.{column}" for column in candidates if column in columns]
    if not available:
        return "NULL"
    return "COALESCE(" + ", ".join(available) + ")"


def _sales_view_family_expression(
    columns: set[str],
    tables_lower: set[str],
    table_columns: Mapping[str, set[str]] | None,
) -> str | None:
    if table_columns is None and "itemsgroups" in tables_lower and "ItemGroupId" in columns:
        return (
            "(\n"
            "                        SELECT ig.Description\n"
            "                        FROM itemsgroups ig\n"
            "                        WHERE ig.Id = v.ItemGroupId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )

    groups_columns = _columns_for_reference(table_columns, "itemsgroups")
    group_description_column = _first_column_name(groups_columns, ("Description", "Name"))
    group_key_column = _first_column_name(groups_columns, ("Id", "KeyId", "GroupId"))
    if "itemsgroups" in tables_lower and group_description_column and group_key_column and "ItemGroupId" in columns:
        return (
            "(\n"
            f"                        SELECT ig.`{group_description_column}`\n"
            "                        FROM itemsgroups ig\n"
            f"                        WHERE ig.`{group_key_column}` = v.ItemGroupId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )

    items_columns = _columns_for_reference(table_columns, "items")
    item_key_column = _first_column_name(items_columns, ("KeyId", "ItemKeyId", "Id"))
    item_group_column = _first_column_name(items_columns, ("GroupId", "ItemGroupId"))
    if (
        {"items", "itemsgroups"} <= tables_lower
        and "ItemKeyId" in columns
        and item_key_column
        and item_group_column
        and group_description_column
        and group_key_column
    ):
        return (
            "(\n"
            f"                        SELECT ig.`{group_description_column}`\n"
            "                        FROM items i\n"
            "                        INNER JOIN itemsgroups ig\n"
            f"                            ON ig.`{group_key_column}` = i.`{item_group_column}`\n"
            f"                        WHERE i.`{item_key_column}` = v.ItemKeyId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )

    return None


def _documents_family_expression(
    body_columns: set[str],
    tables_lower: set[str],
    table_columns: Mapping[str, set[str]],
) -> str:
    groups_columns = _columns_for_reference(table_columns, "itemsgroups")
    group_description_column = _first_column_name(groups_columns, ("Description", "Name"))
    group_key_column = _first_column_name(groups_columns, ("Id", "KeyId", "GroupId"))
    if "itemsgroups" in tables_lower and "ItemGroupId" in body_columns and group_description_column and group_key_column:
        return (
            "(\n"
            f"                        SELECT ig.`{group_description_column}`\n"
            "                        FROM itemsgroups ig\n"
            f"                        WHERE ig.`{group_key_column}` = b.ItemGroupId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )

    items_columns = _columns_for_reference(table_columns, "items")
    item_key_column = _first_column_name(items_columns, ("KeyId", "ItemKeyId", "Id"))
    item_group_column = _first_column_name(items_columns, ("GroupId", "ItemGroupId"))
    if (
        {"items", "itemsgroups"} <= tables_lower
        and "ItemKeyId" in body_columns
        and item_key_column
        and item_group_column
        and group_description_column
        and group_key_column
    ):
        return (
            "(\n"
            f"                        SELECT ig.`{group_description_column}`\n"
            "                        FROM items i\n"
            "                        INNER JOIN itemsgroups ig\n"
            f"                            ON ig.`{group_key_column}` = i.`{item_group_column}`\n"
            f"                        WHERE i.`{item_key_column}` = b.ItemKeyId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )

    return _literal("NULL", "familia_produto")


def _columns_for_reference(table_columns: Mapping[str, set[str]] | None, table_name: str) -> set[str]:
    if table_columns is None:
        return set()
    return _columns_for(table_columns, table_name)


def _first_column_name(columns: set[str], candidates: tuple[str, ...]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        match = lowered.get(candidate.lower())
        if match:
            return match
    return None

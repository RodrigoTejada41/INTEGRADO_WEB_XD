from __future__ import annotations

from datetime import UTC
from typing import Mapping


AUTO_SOURCE_QUERY = "auto"

OPTIONAL_CANONICAL_FIELDS = (
    "branch_code",
    "terminal_code",
    "tipo_venda",
    "forma_pagamento",
    "familia_produto",
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
            item[field] = str(value).strip()

    return item


def build_xd_salesdocuments_query(columns: set[str], tables: set[str]) -> str:
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

    optional_selects = [
        _literal("'0001'", "branch_code"),
        _column("v", "Terminal", "terminal_code", columns),
        _column("v", "DocumentDescription", "tipo_venda", columns),
    ]

    if {"itemsgroups"} <= tables and "ItemGroupId" in columns:
        optional_selects.append(
            "(\n"
            "                        SELECT ig.Description\n"
            "                        FROM itemsgroups ig\n"
            "                        WHERE ig.Id = v.ItemGroupId\n"
            "                        LIMIT 1\n"
            "                    ) AS familia_produto"
        )
    elif "ItemGroupId" in columns:
        optional_selects.append(_column("v", "ItemGroupId", "familia_produto", columns))
    else:
        optional_selects.append(_literal("NULL", "familia_produto"))

    if {"invoicepaymentdetails", "xconfigpaymenttypes"} <= tables and {"Number", "SerieId"} <= columns:
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


def _column(alias: str, column: str, output: str, columns: set[str]) -> str:
    if column not in columns:
        return _literal("NULL", output)
    return f"{alias}.{column} AS {output}"


def _literal(value: str, output: str) -> str:
    return f"{value} AS {output}"

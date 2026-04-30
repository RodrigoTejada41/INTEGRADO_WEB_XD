from __future__ import annotations

from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")


def build_report_pdf_summary(
    *,
    overview: dict,
    product_rows: list[dict],
    payment_rows: list[dict],
) -> dict[str, object]:
    return {
        "products": _product_summary(overview, product_rows),
        "payments": _payment_summary(payment_rows),
    }


def _product_summary(overview: dict, product_rows: list[dict]) -> dict[str, object]:
    return {
        "has_data": bool(product_rows) or _to_int(overview.get("total_records")) > 0,
        "empty_message": "Nenhum produto encontrado para os filtros aplicados.",
        "total_items": _to_decimal(overview.get("total_quantity")),
        "gross_value": _to_decimal(overview.get("total_gross_value")),
        "net_value": _to_decimal(overview.get("total_sales_value")),
        "discount_value": _to_decimal(overview.get("total_discount_value")),
        "surcharge_value": _to_decimal(overview.get("total_surcharge_value")),
        "final_value": _to_decimal(overview.get("total_sales_value")),
    }


def _payment_summary(payment_rows: list[dict]) -> dict[str, object]:
    subtotals = []
    total_records = 0
    total_transactions = 0
    total_value = ZERO

    for row in payment_rows:
        record_count = _to_int(row.get("total_records"))
        subtotal = _to_decimal(row.get("total_sales_value"))
        transaction_count = _to_int(row.get("transaction_count", row.get("total_records")))
        subtotals.append(
            {
                "label": row.get("label") or "Nao informado",
                "transaction_count": transaction_count,
                "total_records": record_count,
                "subtotal": subtotal,
            }
        )
        total_records += record_count
        total_transactions += transaction_count
        total_value += subtotal

    return {
        "has_data": bool(payment_rows),
        "empty_message": "Nenhum pagamento encontrado para os filtros aplicados.",
        "subtotals": subtotals,
        "total_records": total_records,
        "transaction_count": total_transactions,
        "grand_total": total_value,
    }


def _to_decimal(value: object) -> Decimal:
    if value in (None, ""):
        return ZERO
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return ZERO


def _to_int(value: object) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return 0

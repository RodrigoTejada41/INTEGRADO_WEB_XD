from __future__ import annotations

import sys
from pathlib import Path


def _ensure_sync_admin_path() -> None:
    sync_admin_root = Path("sync-admin").resolve()
    if str(sync_admin_root) not in sys.path:
        sys.path.insert(0, str(sync_admin_root))


def test_payment_breakdown_is_grouped_by_payment_name() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    items = [
        {
            "label": "Rede Credito",
            "total_records": 10,
            "quantity_sold": 20,
            "gross_value": 100,
            "discount_value": 4,
            "surcharge_value": 1,
            "total_sales_value": 97,
        },
        {
            "label": "Dinheiro, Rede Credito",
            "total_records": 4,
            "quantity_sold": 8,
            "gross_value": 40,
            "discount_value": 0,
            "surcharge_value": 0,
            "total_sales_value": 40,
        },
        {
            "label": "Rede Credito, Rede Credito",
            "total_records": 2,
            "quantity_sold": 2,
            "gross_value": 20,
            "discount_value": 0,
            "surcharge_value": 0,
            "total_sales_value": 20,
        },
    ]

    normalized = pages._normalize_payment_breakdown_items(items)
    labels = [item["label"] for item in normalized]

    assert labels == ["Rede Credito", "Dinheiro"]
    assert all("," not in label for label in labels)
    assert sum(float(item["total_sales_value"]) for item in normalized) == 157.0
    assert normalized[0]["total_records"] == "14"
    assert normalized[1]["total_records"] == "2"


def test_kpi_cards_show_explicit_growth_and_sync_states() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    cards = pages._build_kpi_cards(
        overview={"total_records": 10, "total_sales_value": "100.00", "distinct_products": 3},
        comparison=None,
        sync_status={
            "status": "offline",
            "label": "Sem agente",
            "last_sync_at": "Sem agente",
            "reason": "Nenhuma API local conectada para o tenant filtrado.",
        },
    )
    card_by_key = {card["key"]: card for card in cards}

    assert card_by_key["growth"]["value"] == "Sem base"
    assert card_by_key["growth"]["tone"] == "neutral"
    assert card_by_key["last_sync"]["value"] == "Sem agente"
    assert card_by_key["last_sync"]["tone"] == "offline"
    assert card_by_key["total_sales"]["value"] == "R$ 100,00"
    assert card_by_key["average_ticket"]["value"] == "R$ 10,00"


def test_kpi_cards_show_new_when_previous_period_has_no_revenue() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    cards = pages._build_kpi_cards(
        overview={"total_records": 10, "total_sales_value": "100.00", "distinct_products": 3},
        comparison={
            "previous_total_sales_value": "0.00",
            "delta_total_sales_value_pct": None,
        },
        sync_status={"status": "online", "last_sync_at": "2026-04-30T02:00+00:00", "reason": "ok"},
    )
    card_by_key = {card["key"]: card for card in cards}

    assert card_by_key["growth"]["value"] == "Novo"
    assert card_by_key["growth"]["tone"] == "success"


def test_report_values_are_formatted_as_brl_currency() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    assert pages._format_brl("1000") == "R$ 1.000,00"
    assert pages._format_brl("1234.5") == "R$ 1.234,50"
    assert pages._format_brl("-10.1") == "R$ -10,10"


def test_report_template_uses_clear_filter_placeholders_and_currency_filter() -> None:
    template = Path("sync-admin/app/templates/partials/report_dashboard_content.html").read_text(
        encoding="utf-8"
    )
    script = Path("sync-admin/app/static/js/reports.js").read_text(encoding="utf-8")

    assert 'placeholder="Nome do produto"' in template
    assert 'placeholder="Codigo local do produto"' in template
    assert "{{ item.valor|brl }}" in template
    assert "{{ item.total_sales_value|brl }}" in template
    assert "parseLocalizedNumber" in script


def test_report_filters_and_group_column_are_simplified() -> None:
    _ensure_sync_admin_path()

    from app.web.routes import pages

    template = Path("sync-admin/app/templates/partials/report_dashboard_content.html").read_text(
        encoding="utf-8"
    )
    action_views = [view for view, *_rest in pages.REPORT_ACTIONS]

    assert "name=\"category\"" not in template
    assert "name=\"card_brand\"" not in template
    assert "Categoria" not in template
    assert "categoria_produto" not in template
    assert "categories" not in template
    assert "<th>Grupo</th>" not in template
    assert "<th>{{ detail_group_label }}</th>" in template
    assert pages.REPORT_VIEW_GROUP_LABELS["families"] == "Familia"
    assert "categories" not in action_views
    assert "card_brands" not in action_views

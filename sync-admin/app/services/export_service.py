from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape


def records_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=['id', 'batch_id', 'record_key', 'record_type', 'event_time', 'created_at'],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def audit_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['timestamp', 'source', 'event', 'detail'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def records_to_markdown(rows: list[dict], *, title: str = 'Registros sincronizados') -> str:
    return _rows_to_markdown(
        title=title,
        rows=rows,
        headers=['id', 'batch_id', 'record_key', 'record_type', 'event_time', 'created_at'],
        sample_limit=25,
    )


def audit_to_markdown(rows: list[dict], *, title: str = 'Auditoria operacional') -> str:
    return _rows_to_markdown(
        title=title,
        rows=rows,
        headers=['timestamp', 'source', 'event', 'detail'],
        sample_limit=25,
    )


def write_markdown_snapshot(path: str | Path, markdown: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown, encoding='utf-8')
    return target


def records_to_xlsx_bytes(rows: list[dict], *, sheet_name: str = 'Records') -> bytes:
    return _build_xlsx([(sheet_name, ['id', 'batch_id', 'record_key', 'record_type', 'event_time', 'created_at'], rows)])


def audit_to_xlsx_bytes(rows: list[dict], *, sheet_name: str = 'Audit') -> bytes:
    return _build_xlsx([(sheet_name, ['timestamp', 'source', 'event', 'detail'], rows)])


def records_to_pdf_bytes(rows: list[dict], *, title: str = 'Registros sincronizados') -> bytes:
    return _build_pdf(_rows_to_text_lines(title, rows, ['id', 'batch_id', 'record_key', 'record_type', 'event_time', 'created_at']))


def audit_to_pdf_bytes(rows: list[dict], *, title: str = 'Auditoria operacional') -> bytes:
    return _build_pdf(_rows_to_text_lines(title, rows, ['timestamp', 'source', 'event', 'detail']))


def report_recent_sales_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            'Data',
            'Codigo Produto',
            'Produto',
            'Quantidade',
            'Valor Bruto',
            'Desconto',
            'Acrescimo',
            'Valor',
            'Pagamento',
            'Bandeira',
            'Tipo',
            'Familia',
            'Filial',
            'Terminal',
            'Operador',
            'Cliente',
            'Status',
            'Cancelada',
            'Codigo',
        ],
        delimiter=';',
        extrasaction='ignore',
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(_client_sale_row(row))
    return output.getvalue()


def report_table_to_csv(headers: list[str], rows: list[dict], totals: dict[str, object]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({header: row.get(header, '') for header in headers})
    writer.writerow({})
    writer.writerow(_totals_export_row(headers, totals))
    return output.getvalue()


def report_table_to_xlsx_bytes(
    headers: list[str],
    rows: list[dict],
    totals: dict[str, object],
    *,
    sheet_name: str = 'Relatorio',
) -> bytes:
    export_rows = [{header: row.get(header, '') for header in headers} for row in rows]
    export_rows.append({})
    export_rows.append(_totals_export_row(headers, totals))
    return _build_xlsx([(sheet_name, headers, export_rows)])


def report_table_to_pdf_bytes(
    headers: list[str],
    rows: list[dict],
    totals: dict[str, object],
    *,
    title: str = 'Relatorio',
    period_label: str | None = None,
) -> bytes:
    document = _PdfDocument(title=title)
    document.heading(title)
    document.paragraph(f'Gerado em: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    if period_label:
        document.paragraph(f'Periodo do relatorio: {period_label}')
    document.table(
        title='Resultado filtrado',
        headers=headers[:6],
        rows=[[row.get(header, '-') for header in headers[:6]] for row in rows[:45]],
        widths=_fit_pdf_widths(headers[:6]),
    )
    document.section('Total geral')
    document.key_values(
        [
            ('Quantidade total', totals.get('Quantidade total', 0)),
            ('Valor bruto total', _format_currency(totals.get('Valor bruto total', 0))),
            ('Desconto total', _format_currency(totals.get('Desconto total', 0))),
            ('Acrescimo total', _format_currency(totals.get('Acrescimo total', 0))),
            ('Valor final total', _format_currency(totals.get('Valor final total', 0))),
        ]
    )
    return document.render()


def report_to_xlsx_bytes(
    overview: dict,
    daily_rows: list[dict],
    top_rows: list[dict],
    recent_rows: list[dict],
) -> bytes:
    overview_rows = [
        {'Indicador': 'Empresa', 'Valor': overview.get('empresa_id', '-')},
        {'Indicador': 'Periodo', 'Valor': f'{overview.get("start_date", "-")} ate {overview.get("end_date", "-")}'},
        {'Indicador': 'Total faturado', 'Valor': overview.get('total_sales_value', 0)},
        {'Indicador': 'Total bruto', 'Valor': overview.get('total_gross_value', 0)},
        {'Indicador': 'Total descontos', 'Valor': overview.get('total_discount_value', 0)},
        {'Indicador': 'Total acrescimos', 'Valor': overview.get('total_surcharge_value', 0)},
        {'Indicador': 'Quantidade vendida', 'Valor': overview.get('total_quantity', 0)},
        {'Indicador': 'Total de registros', 'Valor': overview.get('total_records', 0)},
        {'Indicador': 'Produtos distintos', 'Valor': overview.get('distinct_products', 0)},
        {'Indicador': 'Filiais distintas', 'Valor': overview.get('distinct_branches', 0)},
        {'Indicador': 'Terminais distintos', 'Valor': overview.get('distinct_terminals', 0)},
        {'Indicador': 'Primeira venda', 'Valor': overview.get('first_sale_date') or '-'},
        {'Indicador': 'Ultima venda', 'Valor': overview.get('last_sale_date') or '-'},
    ]
    daily_export_rows = [
        {
            'Dia': row.get('day', '-'),
            'Registros': row.get('total_records', 0),
            'Valor': row.get('total_sales_value', 0),
        }
        for row in daily_rows
    ]
    top_export_rows = [
        {
            'Produto': row.get('produto', '-'),
            'Codigo Produto': row.get('codigo_produto_local', '-'),
            'Familia': row.get('familia_produto', '-'),
            'Registros': row.get('total_records', 0),
            'Quantidade': row.get('quantity_sold', 0),
            'Valor Bruto': row.get('gross_value', 0),
            'Desconto': row.get('discount_value', 0),
            'Acrescimo': row.get('surcharge_value', 0),
            'Valor': row.get('total_sales_value', 0),
        }
        for row in top_rows
    ]
    recent_export_rows = [_client_sale_row(row) for row in recent_rows]
    return _build_xlsx(
        [
            ('Resumo', ['Indicador', 'Valor'], overview_rows),
            (
                'Vendas',
                [
                    'Data',
                    'Codigo Produto',
                    'Produto',
                    'Quantidade',
                    'Valor Bruto',
                    'Desconto',
                    'Acrescimo',
                    'Valor',
                    'Pagamento',
                    'Bandeira',
                    'Tipo',
                    'Familia',
                    'Filial',
                    'Terminal',
                    'Operador',
                    'Cliente',
                    'Status',
                    'Cancelada',
                    'Codigo',
                ],
                recent_export_rows,
            ),
            (
                'Produtos',
                [
                    'Codigo Produto',
                    'Produto',
                    'Familia',
                    'Registros',
                    'Quantidade',
                    'Valor Bruto',
                    'Desconto',
                    'Acrescimo',
                    'Valor',
                ],
                top_export_rows,
            ),
            ('Dias', ['Dia', 'Registros', 'Valor'], daily_export_rows),
        ]
    )


def _client_sale_row(row: dict) -> dict[str, object]:
    return {
        'Data': row.get('data') or row.get('data_atualizacao') or '-',
        'Codigo Produto': row.get('codigo_produto_local') or '-',
        'Produto': row.get('produto') or '-',
        'Quantidade': row.get('quantidade') or row.get('quantity_sold') or 0,
        'Valor Bruto': row.get('valor_bruto') or row.get('gross_value') or 0,
        'Desconto': row.get('desconto') or row.get('discount_value') or 0,
        'Acrescimo': row.get('acrescimo') or row.get('surcharge_value') or 0,
        'Valor': row.get('valor') or row.get('total_sales_value') or 0,
        'Pagamento': row.get('forma_pagamento') or '-',
        'Bandeira': row.get('bandeira_cartao') or '-',
        'Tipo': row.get('tipo_venda') or '-',
        'Familia': row.get('familia_produto') or '-',
        'Filial': row.get('branch_code') or '-',
        'Terminal': row.get('terminal_code') or '-',
        'Operador': row.get('operador') or '-',
        'Cliente': row.get('cliente') or '-',
        'Status': row.get('status_venda') or '-',
        'Cancelada': 'sim' if row.get('cancelada') else 'nao',
        'Codigo': row.get('uuid') or '-',
    }


def _totals_export_row(headers: list[str], totals: dict[str, object]) -> dict[str, object]:
    row = {header: '' for header in headers}
    first_header = headers[0] if headers else 'Total'
    row[first_header] = 'TOTAL GERAL'
    for key, value in totals.items():
        if key in row:
            row[key] = value
    return row


def _fit_pdf_widths(headers: list[str]) -> list[int]:
    if not headers:
        return []
    width = max(55, int(500 / len(headers)))
    return [width for _ in headers]


def report_to_pdf_bytes(
    overview: dict,
    daily_rows: list[dict],
    top_rows: list[dict],
    recent_rows: list[dict],
    payment_rows: list[dict] | None = None,
    financial_summary: dict[str, object] | None = None,
    *,
    title: str = 'Relatorios',
) -> bytes:
    payment_rows = payment_rows or []
    financial_summary = financial_summary or {}
    document = _PdfDocument(title=title)
    document.heading(title)
    document.paragraph(f'Gerado em: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}')

    document.section('Filtros e resumo')
    document.key_values(
        [
            ('Empresa', overview.get('empresa_id', '-')),
            ('Periodo', _format_period_label(overview.get('start_date'), overview.get('end_date'))),
            ('Filial', overview.get('branch_code') or 'Todas'),
            ('Terminal', overview.get('terminal_code') or 'Todos'),
            ('Horario', f'{overview.get("start_time") or "00:00"} ate {overview.get("end_time") or "23:59"}'),
        ]
    )

    document.section('Indicadores')
    document.key_values(
        [
            ('Total de registros', overview.get('total_records', 0)),
            ('Total faturado', _format_currency(overview.get('total_sales_value', 0))),
            ('Total bruto', _format_currency(overview.get('total_gross_value', 0))),
            ('Descontos', _format_currency(overview.get('total_discount_value', 0))),
            ('Acrescimos', _format_currency(overview.get('total_surcharge_value', 0))),
            ('Quantidade', _format_quantity(overview.get('total_quantity', 0))),
            ('Produtos distintos', overview.get('distinct_products', 0)),
            ('Filiais distintas', overview.get('distinct_branches', 0)),
            ('Terminais distintos', overview.get('distinct_terminals', 0)),
            ('Primeira venda', overview.get('first_sale_date') or '-'),
            ('Ultima venda', overview.get('last_sale_date') or '-'),
        ]
    )

    document.table(
        title='Serie diaria',
        headers=['Dia', 'Registros', 'Valor'],
        rows=[
            [row.get('day', '-'), row.get('total_records', 0), _format_currency(row.get('total_sales_value', 0))]
            for row in daily_rows[:25]
        ],
        widths=[110, 90, 130],
    )
    document.table(
        title='Top produtos',
        headers=['Codigo', 'Produto', 'Qtd', 'Valor'],
        rows=[
            [
                row.get('codigo_produto_local', '-'),
                row.get('produto', '-'),
                _format_quantity(row.get('quantity_sold', row.get('total_records', 0))),
                _format_currency(row.get('total_sales_value', 0)),
            ]
            for row in top_rows[:25]
        ],
        widths=[80, 230, 70, 100],
    )
    document.summary_box(
        title='Resumo financeiro de produtos',
        rows=_product_summary_rows(financial_summary.get('products')),
        empty_message=_empty_message(financial_summary.get('products')),
    )
    document.table(
        title='Total por forma de pagamento',
        headers=['Pagamento', 'Transacoes', 'Subtotal'],
        rows=[
            [
                row.get('label', '-'),
                row.get('transaction_count', row.get('total_records', 0)),
                _format_currency(row.get('subtotal', row.get('total_sales_value', 0))),
            ]
            for row in _payment_subtotals(financial_summary.get('payments'), payment_rows)
        ],
        widths=[230, 90, 130],
    )
    document.summary_box(
        title='Resumo financeiro de pagamentos',
        rows=_payment_summary_rows(financial_summary.get('payments')),
        empty_message=_empty_message(financial_summary.get('payments')),
    )
    document.table(
        title='Vendas recentes',
        headers=['Codigo', 'Produto', 'Qtd', 'Valor', 'Pagamento', 'Data'],
        rows=[
            [
                row.get('codigo_produto_local') or row.get('uuid', '-'),
                row.get('produto', '-'),
                _format_quantity(row.get('quantidade', 1)),
                _format_currency(row.get('valor_liquido') or row.get('valor', 0)),
                row.get('forma_pagamento', '-'),
                row.get('data', '-'),
            ]
            for row in recent_rows[:35]
        ],
        widths=[75, 180, 45, 70, 90, 70],
    )
    return document.render()


def _product_summary_rows(summary: object) -> list[tuple[str, object]]:
    if not isinstance(summary, dict):
        return _zero_product_summary_rows()
    return [
        ('Quantidade total de itens', _format_quantity(summary.get('total_items', 0))),
        ('Valor total bruto', _format_currency(summary.get('gross_value', 0))),
        ('Valor total liquido', _format_currency(summary.get('net_value', 0))),
        ('Total de descontos', _format_currency(summary.get('discount_value', 0))),
        ('Total de acrescimos', _format_currency(summary.get('surcharge_value', 0))),
        ('Total final', _format_currency(summary.get('final_value', 0))),
    ]


def _zero_product_summary_rows() -> list[tuple[str, object]]:
    return [
        ('Quantidade total de itens', _format_quantity(0)),
        ('Valor total bruto', _format_currency(0)),
        ('Valor total liquido', _format_currency(0)),
        ('Total de descontos', _format_currency(0)),
        ('Total de acrescimos', _format_currency(0)),
        ('Total final', _format_currency(0)),
    ]


def _payment_summary_rows(summary: object) -> list[tuple[str, object]]:
    if not isinstance(summary, dict):
        return [('Total geral', _format_currency(0)), ('Transacoes', 0)]
    return [
        ('Total geral', _format_currency(summary.get('grand_total', 0))),
        ('Transacoes', summary.get('transaction_count', summary.get('total_records', 0))),
    ]


def _payment_subtotals(summary: object, fallback_rows: list[dict]) -> list[dict]:
    if isinstance(summary, dict) and isinstance(summary.get('subtotals'), list):
        return list(summary['subtotals'])
    return fallback_rows


def _empty_message(summary: object) -> str | None:
    if not isinstance(summary, dict) or summary.get('has_data', True):
        return None
    return str(summary.get('empty_message') or 'Sem dados para o filtro atual.')


def _rows_to_markdown(*, title: str, rows: list[dict], headers: list[str], sample_limit: int) -> str:
    lines = [
        f'# {title}',
        '',
        f'- Gerado em: {datetime.now(timezone.utc).isoformat()}',
        f'- Total de registros: {len(rows)}',
        '',
        '## Amostra',
        '',
        '| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join(['---'] * len(headers)) + ' |',
    ]
    for row in rows[:sample_limit]:
        lines.append('| ' + ' | '.join(str(row.get(header, '-')) for header in headers) + ' |')
    return '\n'.join(lines) + '\n'


def _rows_to_text_lines(title: str, rows: list[dict], headers: list[str]) -> list[str]:
    lines = [
        _pdf_escape(title),
        _pdf_escape(f'Total: {len(rows)}'),
        '',
    ]
    for row in rows[:40]:
        lines.append(_pdf_escape(' | '.join(str(row.get(header, '-')) for header in headers)))
    return lines


def _build_xlsx(sheets: list[tuple[str, list[str], list[dict]]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        sheet_names = [sheet_name for sheet_name, _, _ in sheets]
        archive.writestr('[Content_Types].xml', _xlsx_content_types(len(sheets)))
        archive.writestr('_rels/.rels', _xlsx_root_rels())
        archive.writestr('docProps/app.xml', _xlsx_app_xml(sheet_names))
        archive.writestr('docProps/core.xml', _xlsx_core_xml())
        archive.writestr('xl/workbook.xml', _xlsx_workbook_xml(sheet_names))
        archive.writestr('xl/_rels/workbook.xml.rels', _xlsx_workbook_rels(len(sheets)))
        archive.writestr('xl/styles.xml', _xlsx_styles_xml())
        for index, (sheet_name, headers, rows) in enumerate(sheets, start=1):
            archive.writestr(f'xl/worksheets/sheet{index}.xml', _xlsx_sheet_xml(sheet_name, headers, rows))
    return buffer.getvalue()


def _xlsx_content_types(sheet_count: int) -> str:
    sheet_overrides = '\n'.join(
        f'  <Override PartName="/xl/worksheets/sheet{index}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheet_overrides}
</Types>'''


def _xlsx_root_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def _xlsx_app_xml(sheet_names: list[str]) -> str:
    title_parts = ''.join(f'<vt:lpstr>{escape(name)}</vt:lpstr>' for name in sheet_names)
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>sync-admin</Application>
  <HeadingPairs>
    <vt:vector size="2" baseType="variant">
      <vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>
      <vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant>
    </vt:vector>
  </HeadingPairs>
  <TitlesOfParts>
    <vt:vector size="{len(sheet_names)}" baseType="lpstr">{title_parts}</vt:vector>
  </TitlesOfParts>
</Properties>'''


def _xlsx_core_xml() -> str:
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>sync-admin</dc:creator>
  <cp:lastModifiedBy>sync-admin</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>'''


def _xlsx_workbook_xml(sheet_names: list[str]) -> str:
    sheets = ''.join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheets}</sheets>
</workbook>'''


def _xlsx_workbook_rels(sheet_count: int) -> str:
    rels = ''.join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
</Relationships>'''


def _xlsx_styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>'''


def _xlsx_sheet_xml(_sheet_name: str, headers: list[str], rows: list[dict]) -> str:
    xml_rows = []
    rows_with_header = [dict(zip(headers, headers))] + rows
    for row_index, row in enumerate(rows_with_header, start=1):
        cells = []
        for column_index, header in enumerate(headers, start=1):
            cell_ref = f'{_xlsx_column_name(column_index)}{row_index}'
            value = escape(str(row.get(header, '')))
            cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{value}</t></is></c>')
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>{''.join(xml_rows)}</sheetData>
</worksheet>'''


def _xlsx_column_name(index: int) -> str:
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _pdf_escape(text: str) -> str:
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _pdf_text(value: object, max_length: int | None = None) -> str:
    text = str(value if value not in (None, '') else '-')
    text = (
        text.replace('á', 'a')
        .replace('à', 'a')
        .replace('ã', 'a')
        .replace('â', 'a')
        .replace('é', 'e')
        .replace('ê', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('õ', 'o')
        .replace('ô', 'o')
        .replace('ú', 'u')
        .replace('ç', 'c')
        .replace('Á', 'A')
        .replace('À', 'A')
        .replace('Ã', 'A')
        .replace('Â', 'A')
        .replace('É', 'E')
        .replace('Ê', 'E')
        .replace('Í', 'I')
        .replace('Ó', 'O')
        .replace('Õ', 'O')
        .replace('Ô', 'O')
        .replace('Ú', 'U')
        .replace('Ç', 'C')
    )
    if max_length and len(text) > max_length:
        return text[: max(0, max_length - 3)] + '...'
    return text


def _format_currency(value: object) -> str:
    number = _to_decimal(value)
    sign = '-' if number < 0 else ''
    number = abs(number).quantize(Decimal('0.01'))
    integer_part, decimal_part = f'{number:.2f}'.split('.')
    groups = []
    while integer_part:
        groups.append(integer_part[-3:])
        integer_part = integer_part[:-3]
    return f'R$ {sign}{".".join(reversed(groups))},{decimal_part}'


def _format_period_label(start_date: object, end_date: object) -> str:
    start = _format_date_br(start_date)
    end = _format_date_br(end_date)
    if start != '-' and end != '-':
        return f'{start} ate {end}'
    if start != '-':
        return f'A partir de {start}'
    if end != '-':
        return f'Ate {end}'
    return 'Todo o periodo'


def _format_date_br(value: object) -> str:
    if value in (None, ''):
        return '-'
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text[:10])
        return parsed.strftime('%d/%m/%Y')
    except ValueError:
        return text


def _format_quantity(value: object) -> str:
    number = _to_decimal(value)
    if number == number.to_integral():
        text = f'{int(number):,}'.replace(',', '.')
        return text
    normalized = f'{number.quantize(Decimal("0.001")):,.3f}'
    return normalized.replace(',', 'X').replace('.', ',').replace('X', '.').rstrip('0').rstrip(',')


def _to_decimal(value: object) -> Decimal:
    if value in (None, ''):
        return Decimal('0')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal('0')


class _PdfDocument:
    def __init__(self, *, title: str) -> None:
        self.title = _pdf_text(title)
        self.pages: list[list[str]] = [[]]
        self.y = 790
        self.left = 42
        self.bottom = 54

    def heading(self, text: str) -> None:
        self._text(self.left, self.y, _pdf_text(text, 72), size=18)
        self.y -= 22
        self._line(self.left, self.y, 553, self.y)
        self.y -= 18

    def section(self, text: str) -> None:
        self._ensure_space(34)
        self.y -= 6
        self._text(self.left, self.y, _pdf_text(text, 72), size=13)
        self.y -= 16

    def paragraph(self, text: str) -> None:
        self._ensure_space(18)
        self._text(self.left, self.y, _pdf_text(text, 95), size=9)
        self.y -= 14

    def key_values(self, rows: list[tuple[str, object]]) -> None:
        for index in range(0, len(rows), 2):
            self._ensure_space(22)
            left = rows[index]
            right = rows[index + 1] if index + 1 < len(rows) else None
            self._key_value_cell(self.left, self.y, left[0], left[1], width=240)
            if right:
                self._key_value_cell(self.left + 265, self.y, right[0], right[1], width=240)
            self.y -= 26
        self.y -= 4

    def summary_box(self, *, title: str, rows: list[tuple[str, object]], empty_message: str | None = None) -> None:
        self.section(title)
        if empty_message:
            self._ensure_space(18)
            self._text(self.left, self.y, _pdf_text(empty_message, 92), size=9)
            self.y -= 16
        for index in range(0, len(rows), 3):
            chunk = rows[index : index + 3]
            self._ensure_space(30)
            for offset, (label, value) in enumerate(chunk):
                self._summary_cell(self.left + offset * 170, self.y, label, value)
            self.y -= 31
        self.y -= 4

    def table(self, *, title: str, headers: list[str], rows: list[list[object]], widths: list[int]) -> None:
        self.section(title)
        self._table_header(headers, widths)
        if not rows:
            self._ensure_space(20)
            self._text(self.left, self.y, 'Sem dados para o filtro atual.', size=9)
            self.y -= 16
            return
        for row in rows:
            self._ensure_space(26)
            if self.y > 760:
                self._table_header(headers, widths)
            self._row(row, widths)
        self.y -= 8

    def render(self) -> bytes:
        page_objects = []
        content_objects = []
        font_object_number = 3 + len(self.pages) * 2
        for index, commands in enumerate(self.pages):
            page_number = 3 + index * 2
            content_number = page_number + 1
            content = ('\n'.join(commands) + '\n').encode('latin-1', 'replace')
            page_objects.append(
                (
                    page_number,
                    (
                        f'{page_number} 0 obj\n'
                        f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
                        f'/Resources << /Font << /F1 {font_object_number} 0 R >> >> '
                        f'/Contents {content_number} 0 R >>\nendobj\n'
                    ).encode('latin-1')
                )
            )
            content_objects.append(
                (
                    content_number,
                    (
                        f'{content_number} 0 obj\n<< /Length {len(content)} >>\nstream\n'
                    ).encode('latin-1')
                    + content
                    + b'endstream\nendobj\n'
                )
            )

        kids = ' '.join(f'{number} 0 R' for number, _ in page_objects)
        objects: list[tuple[int, bytes]] = [
            (1, b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'),
            (2, f'2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>\nendobj\n'.encode('latin-1')),
        ]
        objects.extend(page_objects)
        objects.extend(content_objects)
        objects.append(
            (
                font_object_number,
                f'{font_object_number} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'.encode('latin-1'),
            )
        )
        return _build_pdf_from_objects(objects)

    def _key_value_cell(self, x: int, y: int, label: str, value: object, *, width: int) -> None:
        self._rect(x, y - 17, width, 22)
        self._text(x + 8, y - 1, _pdf_text(label, 26), size=7)
        self._text(x + 8, y - 11, _pdf_text(value, 34), size=9)

    def _summary_cell(self, x: int, y: int, label: str, value: object) -> None:
        self._rect(x, y - 21, 158, 27, fill='0.90 0.95 1 rg')
        self._text(x + 8, y - 1, _pdf_text(label, 24), size=7)
        self._text(x + 8, y - 13, _pdf_text(value, 24), size=10)

    def _table_header(self, headers: list[str], widths: list[int]) -> None:
        self._ensure_space(28)
        x = self.left
        self._rect(self.left, self.y - 15, sum(widths), 20, fill='0.92 0.96 1 rg')
        for header, width in zip(headers, widths):
            self._text(x + 4, self.y - 8, _pdf_text(header, max(8, width // 6)), size=8)
            x += width
        self.y -= 22

    def _row(self, row: list[object], widths: list[int]) -> None:
        x = self.left
        row_height = 20
        self._line(self.left, self.y - 15, self.left + sum(widths), self.y - 15)
        for value, width in zip(row, widths):
            self._text(x + 4, self.y - 8, _pdf_text(value, max(8, width // 6)), size=8)
            x += width
        self.y -= row_height

    def _ensure_space(self, height: int) -> None:
        if self.y - height >= self.bottom:
            return
        self.pages.append([])
        self.y = 790

    def _text(self, x: int, y: int, text: str, *, size: int) -> None:
        self.pages[-1].append(f'BT /F1 {size} Tf {x} {y} Td ({_pdf_escape(text)}) Tj ET')

    def _line(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.pages[-1].append(f'0.75 0.82 0.9 RG {x1} {y1} m {x2} {y2} l S')

    def _rect(self, x: int, y: int, width: int, height: int, *, fill: str = '0.98 0.99 1 rg') -> None:
        self.pages[-1].append(f'q {fill} {x} {y} {width} {height} re f Q')


def _build_pdf(lines: list[str]) -> bytes:
    content_lines = ['BT', '/F1 10 Tf', '72 770 Td']
    first_line = True
    for line in lines:
        if line == '':
            content_lines.append('T*')
            continue
        if first_line:
            content_lines.append(f'({line}) Tj')
            first_line = False
        else:
            content_lines.append(f'T* ({line}) Tj')
    content_lines.append('ET')
    content = '\n'.join(content_lines).encode('utf-8')

    objects = [
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
        (
            b'3 0 obj\n'
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n'
            b'endobj\n'
        ),
        b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n',
        b'5 0 obj\n<< /Length ' + str(len(content)).encode('utf-8') + b' >>\nstream\n' + content + b'\nendstream\nendobj\n',
    ]

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('utf-8'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('utf-8'))
    pdf.extend(
        b'trailer\n'
        + f'<< /Size {len(objects) + 1} /Root 1 0 R >>\n'.encode('utf-8')
        + b'startxref\n'
        + f'{xref_offset}\n'.encode('utf-8')
        + b'%%EOF'
    )
    return bytes(pdf)


def _build_pdf_from_objects(objects: list[tuple[int, bytes]]) -> bytes:
    ordered = sorted(objects, key=lambda item: item[0])
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = {0: 0}
    for number, obj in ordered:
        offsets[number] = len(pdf)
        pdf.extend(obj)
    max_object = max(offsets)
    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {max_object + 1}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for number in range(1, max_object + 1):
        offset = offsets.get(number, 0)
        if offset:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('latin-1'))
        else:
            pdf.extend(b'0000000000 65535 f \n')
    pdf.extend(
        b'trailer\n'
        + f'<< /Size {max_object + 1} /Root 1 0 R >>\n'.encode('latin-1')
        + b'startxref\n'
        + f'{xref_offset}\n'.encode('latin-1')
        + b'%%EOF'
    )
    return bytes(pdf)

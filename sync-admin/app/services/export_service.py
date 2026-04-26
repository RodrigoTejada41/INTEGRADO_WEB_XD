from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timezone
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
            'uuid',
            'produto',
            'valor',
            'data',
            'data_atualizacao',
            'branch_code',
            'terminal_code',
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def report_to_xlsx_bytes(
    overview: dict,
    daily_rows: list[dict],
    top_rows: list[dict],
    recent_rows: list[dict],
) -> bytes:
    overview_rows = [{'metric': key, 'value': value} for key, value in overview.items()]
    return _build_xlsx(
        [
            ('Overview', ['metric', 'value'], overview_rows),
            ('DailySales', ['day', 'total_records', 'total_sales_value'], daily_rows),
            ('TopProducts', ['produto', 'total_records', 'total_sales_value'], top_rows),
            (
                'RecentSales',
                ['uuid', 'produto', 'valor', 'data', 'data_atualizacao', 'branch_code', 'terminal_code'],
                recent_rows,
            ),
        ]
    )


def report_to_pdf_bytes(
    overview: dict,
    daily_rows: list[dict],
    top_rows: list[dict],
    recent_rows: list[dict],
    *,
    title: str = 'Relatorios',
) -> bytes:
    overview_lines = [f'{key}: {value}' for key, value in overview.items()]
    daily_lines = [
        'Serie diaria:',
        *[
            f'{row.get("day", "-")} | {row.get("total_records", 0)} | {row.get("total_sales_value", 0)}'
            for row in daily_rows[:15]
        ],
    ]
    top_lines = [
        'Top produtos:',
        *[
            f'{row.get("produto", "-")} | {row.get("total_records", 0)} | {row.get("total_sales_value", 0)}'
            for row in top_rows[:15]
        ],
    ]
    recent_lines = [
        'Vendas recentes:',
        *[
            f'{row.get("uuid", "-")} | {row.get("produto", "-")} | {row.get("valor", 0)} | {row.get("data", "-")}'
            for row in recent_rows[:20]
        ],
    ]
    return _build_pdf(
        [_pdf_escape(title), '']
        + [_pdf_escape(line) for line in overview_lines]
        + ['']
        + [_pdf_escape(line) for line in daily_lines]
        + ['']
        + [_pdf_escape(line) for line in top_lines]
        + ['']
        + [_pdf_escape(line) for line in recent_lines]
    )


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
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


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

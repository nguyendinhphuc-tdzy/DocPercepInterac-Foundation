"""Deterministic synthetic Office fixtures; no customer files or mutation path."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def package(parts: dict[str, str | bytes]) -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED) as archive:
        for name, content in sorted(parts.items()):
            info = ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = ZIP_STORED
            info.create_system = 0
            archive.writestr(info, content.encode("utf-8") if isinstance(content, str) else content)
    return stream.getvalue()


def relationships(items: list[tuple[str, str, str, bool]]) -> str:
    return f'<Relationships xmlns="{P}">' + "".join(
        f'<Relationship Id="{key}" Type="{kind}" Target="{target}"'
        + (' TargetMode="External"' if external else '') + '/>'
        for key, kind, target, external in items
    ) + '</Relationships>'


def content_types(overrides: dict[str, str]) -> str:
    return f'<Types xmlns="{CT}"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' + "".join(
        f'<Override PartName="/{name}" ContentType="{kind}"/>' for name, kind in sorted(overrides.items())
    ) + '</Types>'


def docx_parts(edge: bool = False) -> dict[str, str]:
    table = '<w:tbl><w:tblPr/><w:tblGrid><w:gridCol w:w="2400"/><w:gridCol w:w="2400"/></w:tblGrid>' + ''.join(
        '<w:tr>' + ''.join(f'<w:tc><w:tcPr/><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>' for cell in row) + '</w:tr>'
        for row in [('Metric', 'Value'), ('NCP', '6.08%')]
    ) + '</w:tbl>'
    body = '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Synthetic Local File</w:t></w:r></w:p><w:p><w:r><w:t xml:space="preserve">NCP current value </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>14.18%</w:t></w:r></w:p>' + table
    extras: dict[str, str] = {}
    rels = [('styles', R + '/styles', 'styles.xml', False)]
    if edge:
        body += '<w:sdt><w:sdtPr><w:id w:val="101"/><w:tag w:val="synthetic-control"/><w:lock w:val="sdtContentLocked"/></w:sdtPr><w:sdtContent><w:p><w:r><w:t>CONTROL_SENTINEL</w:t></w:r></w:p></w:sdtContent></w:sdt><w:p><w:bookmarkStart w:id="1" w:name="syntheticBookmark"/><w:r><w:t>BOOKMARK_SENTINEL</w:t></w:r><w:bookmarkEnd w:id="1"/></w:p><w:p><w:fldSimple w:instr="DATE"><w:r><w:t>FIELD_SENTINEL</w:t></w:r></w:fldSimple><w:hyperlink r:id="link"><w:r><w:t>LINK_SENTINEL</w:t></w:r></w:hyperlink></w:p><w:p><w:ins w:id="2" w:author="Synthetic" w:date="2026-09-08T00:00:00Z"><w:r><w:t>REVISION_SENTINEL</w:t></w:r></w:ins></w:p>'
        rels += [('link', R + '/hyperlink', 'https://example.invalid/synthetic', True), ('header', R + '/header', 'header1.xml', False)]
        extras['word/header1.xml'] = f'<w:hdr xmlns:w="{W}"><w:p><w:r><w:t>HEADER_SENTINEL</w:t></w:r></w:p></w:hdr>'
    body += '<w:sectPr>' + ('<w:headerReference w:type="default" r:id="header"/>' if edge else '') + '<w:pgSz w:w="12240" w:h="15840"/></w:sectPr>'
    overrides = {'word/document.xml': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml', 'word/styles.xml': 'application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml'}
    if edge:
        overrides['word/header1.xml'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml'
    return {
        '[Content_Types].xml': content_types(overrides),
        '_rels/.rels': relationships([('main', R + '/officeDocument', 'word/document.xml', False)]),
        'word/document.xml': f'<w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}</w:body></w:document>',
        'word/styles.xml': f'<w:styles xmlns:w="{W}"><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style></w:styles>',
        'word/_rels/document.xml.rels': relationships(rels), **extras,
    }


def xlsx_parts() -> dict[str, str]:
    return {
        '[Content_Types].xml': content_types({
            'xl/workbook.xml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
            'xl/worksheets/sheet1.xml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml',
            'xl/worksheets/sheet2.xml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml',
            'xl/tables/table1.xml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml',
        }),
        '_rels/.rels': relationships([('main', R + '/officeDocument', 'xl/workbook.xml', False)]),
        'xl/workbook.xml': f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets><sheet name="Financial" sheetId="1" r:id="sheet1"/><sheet name="Notes" sheetId="2" r:id="sheet2"/></sheets><definedNames><definedName name="NCP">Financial!$B$2</definedName></definedNames></workbook>',
        'xl/_rels/workbook.xml.rels': relationships([('sheet1', R + '/worksheet', 'worksheets/sheet1.xml', False), ('sheet2', R + '/worksheet', 'worksheets/sheet2.xml', False)]),
        'xl/worksheets/sheet1.xml': f'<worksheet xmlns="{S}" xmlns:r="{R}"><dimension ref="A1:B3"/><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Metric</t></is></c><c r="B1" t="inlineStr"><is><t>Value</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>NCP</t></is></c><c r="B2"><f>6.08/100</f><v>0.0608</v></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>Prior NCP</t></is></c><c r="B3"><v>0.1418</v></c></row></sheetData><tableParts count="1"><tablePart r:id="table1"/></tableParts></worksheet>',
        'xl/worksheets/_rels/sheet1.xml.rels': relationships([('table1', R + '/table', '../tables/table1.xml', False)]),
        'xl/tables/table1.xml': f'<table xmlns="{S}" id="1" name="FinancialTable" displayName="FinancialTable" ref="A1:B3" totalsRowShown="0"><autoFilter ref="A1:B3"/><tableColumns count="2"><tableColumn id="1" name="Metric"/><tableColumn id="2" name="Value"/></tableColumns></table>',
        'xl/worksheets/sheet2.xml': f'<worksheet xmlns="{S}"><dimension ref="A1:B1"/><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>NOTES_SENTINEL</t></is></c></row></sheetData><mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells></worksheet>',
    }


def large_xlsx_parts(rows=(1000,), cells=10, formulas=False):
    """Deterministic variable-scale workbook; never consumes private documents."""
    names=[f'xl/worksheets/sheet{i+1}.xml' for i in range(len(rows))]
    return {
        '[Content_Types].xml':content_types({'xl/workbook.xml':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
            **{n:'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml' for n in names}}),
        '_rels/.rels':relationships([('main',R+'/officeDocument','xl/workbook.xml',False)]),
        'xl/workbook.xml':f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets>'+''.join(f'<sheet name="Synthetic{i}" sheetId="{i}" r:id="s{i}"/>' for i in range(1,len(rows)+1))+'</sheets></workbook>',
        'xl/_rels/workbook.xml.rels':relationships([(f's{i+1}',R+'/worksheet',f'worksheets/sheet{i+1}.xml',False) for i in range(len(rows))]),
        **{name:f'<worksheet xmlns="{S}"><sheetData>'+(''.join('<row>'+('<c>'+('<f>1+1</f><v>2</v>' if formulas else '')+'</c>')*cells+'</row>' for _ in range(count)))+'</sheetData></worksheet>' for name,count in zip(names,rows)},
    }


def build(root: Path) -> dict:
    cases = [
        ('docx-basic', 'DOCX', package(docx_parts()), ['headings', 'paragraphs', 'multiple_runs', 'table']),
        ('docx-native-edge', 'DOCX', package(docx_parts(True)), ['content_control', 'bookmark', 'field', 'hyperlink', 'revision', 'header', 'table']),
        ('xlsx-basic', 'XLSX', package(xlsx_parts()), ['multiple_sheets', 'formula_cached_value', 'defined_name', 'table', 'merged_cells']),
        ('malformed', 'DOCX', b'PK\x03\x04synthetic-truncated-package', ['malformed_package']),
    ]
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'evaluation_version': '1.0.0', 'qualification_kind': 'SYNTHETIC_ONLY', 'engine': 'docling-slim', 'engine_version': '2.126.0', 'run_count': 3, 'cases': []}
    for key, fmt, data, features in cases:
        filename = key + '.' + fmt.lower()
        (root / filename).write_bytes(data)
        manifest['cases'].append({'case_id': key, 'input_path': filename, 'input_sha256': hashlib.sha256(data).hexdigest(), 'format': fmt, 'feature_profile': features, 'expected_conversion': 'FAIL' if key == 'malformed' else 'PASS'})
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    build(Path('tests/golden/cases/b1'))

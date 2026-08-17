"""Parse capability: Geometry Layer (deterministic, no AI).

Docling has been removed (decision confirmed 2026-08-11, per
Foundation_Build_Plan_v4.md mục 0 điểm 4 + STATUS.md) — replaced by
python-docx for DOCX and pdfplumber (+ pdf2image for page rendering) for
PDF. This is the "extract_geometry" step of the v3 pipeline:

    file_intake -> extract_geometry -> group_into_elements -> assign_anchors

group_into_elements lives in element_classifier.py (not yet built);
assign_anchors lives in anchor_builder.py (perception/anchor_builder.py) —
this module only produces raw geometry blocks, one per paragraph/table-cell
(DOCX), cell (XLSX), or text line (PDF), in document order. No
classification, no anchors, no AI.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, TypedDict

import pdfplumber
from docx import Document as DocxDocument


class GeometryBlock(TypedDict):
    text: str
    # DOCX fields
    paragraph_index: Optional[int]
    style_id: Optional[str]
    table_index: Optional[int]
    table_hash: Optional[str]
    row_index: Optional[int]
    col_index: Optional[int]
    # PDF fields
    page: Optional[int]
    bbox: Optional[tuple[float, float, float, float]]  # (x0, top, x1, bottom), pt
    page_width: Optional[float]  # pt — for anchor_builder.py's bbox_relative
    page_height: Optional[float]  # pt
    # XLSX fields
    sheet_name: Optional[str]
    cell_address: Optional[str]
    named_range: Optional[str]
    row_label: Optional[str]  # this row's leftmost non-empty cell — for anchor_builder.py's row self-heal


def parse_docx(path: str) -> list[GeometryBlock]:
    """Deterministic DOCX geometry via python-docx.

    One block per non-empty paragraph (in body order) plus one block per
    table cell — including empty ones, which are real fill-in placeholders,
    not noise — tagged with the same indices AnchorDOCX expects
    (perception/models.py) so anchor_builder.py can consume this directly.
    """
    doc = DocxDocument(path)
    blocks: list[GeometryBlock] = []

    for i, para in enumerate(doc.paragraphs):
        if not para.text.strip():
            continue
        blocks.append(
            {
                "text": para.text,
                "paragraph_index": i,
                "style_id": para.style.style_id if para.style else None,
                "table_index": None,
                "table_hash": None,
                "row_index": None,
                "col_index": None,
                "page": None,
                "bbox": None,
                "page_width": None,
                "page_height": None,
                "sheet_name": None,
                "cell_address": None,
                "named_range": None,
                "row_label": None,
            }
        )

    for t_idx, table in enumerate(doc.tables):
        # Compute Anti-Drift hash for this table
        from perception.anchor_builder import build_table_hash
        t_hash = build_table_hash(table)
        
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                # Unlike paragraphs, empty table cells are kept — a blank
                # cell in a financial template is a real placeholder a
                # user (or a mapping rule) is meant to fill in, not noise.
                # Skipping it would mean it never becomes an Element and
                # so can never be shown, highlighted, or manually edited
                # in the UI, even though it visibly exists in the document.
                blocks.append(
                    {
                        "text": cell.text,
                        "paragraph_index": None,
                        "style_id": None,
                        "table_index": t_idx,
                        "table_hash": t_hash,
                        "row_index": r_idx,
                        "col_index": c_idx,
                        "page": None,
                        "bbox": None,
                        "page_width": None,
                        "page_height": None,
                        "sheet_name": None,
                        "cell_address": None,
                        "named_range": None,
                        "row_label": None,
                    }
                )

    return blocks


def parse_pdf(path: str) -> list[GeometryBlock]:
    """Deterministic PDF geometry via pdfplumber — one block per text line,
    with its bounding box in PDF points (top-left origin, matches AnchorPDF).

    Only extracts text that already has a text layer. Scanned/image-only
    PDFs (no text layer) return zero blocks — OCR is a separate, not-yet-
    decided concern (see STATUS.md fixture_report.pdf note).
    """
    blocks: list[GeometryBlock] = []
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            for line in page.extract_text_lines():
                text = line["text"]
                if not text.strip():
                    continue
                blocks.append(
                    {
                        "text": text,
                        "paragraph_index": None,
                        "style_id": None,
                        "table_index": None,
                        "row_index": None,
                        "col_index": None,
                        "page": page_num,
                        "bbox": (line["x0"], line["top"], line["x1"], line["bottom"]),
                        "page_width": page.width,
                        "page_height": page.height,
                        "sheet_name": None,
                        "cell_address": None,
                        "named_range": None,
                        "row_label": None,
                    }
                )
    return blocks


def parse_xlsx(path: str) -> list[GeometryBlock]:
    """Deterministic XLSX geometry via openpyxl.
    
    Reads all sheets and non-empty cells. Handles named ranges exhaustively
    per user request to ensure no elements are missed or misread.
    """
    import openpyxl
    from openpyxl.utils import range_boundaries

    blocks: list[GeometryBlock] = []
    wb = openpyxl.load_workbook(path, data_only=True, read_only=False)

    # 1. Build a map of cell coordinates to named ranges
    named_ranges_map = {}
    if wb.defined_names:
        for dn in wb.defined_names.values():
            try:
                destinations = list(dn.destinations)
                for sheet_name, coord in destinations:
                    # coord could be a range like "A1:C3" or single cell "A1"
                    min_col, min_row, max_col, max_row = range_boundaries(coord)
                    # To be fully exhaustive, map every cell in the range to this name
                    for row in range(min_row, max_row + 1):
                        for col in range(min_col, max_col + 1):
                            cell_address = openpyxl.utils.get_column_letter(col) + str(row)
                            key = f"{sheet_name}!{cell_address}"
                            if key not in named_ranges_map:
                                named_ranges_map[key] = []
                            named_ranges_map[key].append(dn.name)
            except Exception:
                # Skip legacy/corrupt named ranges that openpyxl cannot parse
                pass

    # 2. Extract cells
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            # Leftmost non-empty cell in the row — the typical financial-
            # statement convention (line-item label in column A/B, values
            # to the right). Shared by every cell in this row so
            # anchor_builder.py can self-heal row insert/delete drift.
            row_label = next(
                (str(c.value).strip() for c in row if c.value is not None), None
            )
            for cell in row:
                if cell.value is not None:
                    # Check for named ranges
                    key = f"{sheet_name}!{cell.coordinate}"
                    nr_list = named_ranges_map.get(key, [])
                    nr_str = ",".join(nr_list) if nr_list else None

                    blocks.append(
                        {
                            "text": str(cell.value).strip(),
                            "paragraph_index": None,
                            "style_id": None,
                            "table_index": None,
                            "row_index": None,
                            "col_index": None,
                            "page": None,
                            "bbox": None,
                            "page_width": None,
                            "page_height": None,
                            "sheet_name": sheet_name,
                            "cell_address": cell.coordinate,
                            "named_range": nr_str,
                            "row_label": row_label,
                        }
                    )

    wb.close()
    return blocks


def render_pdf_pages(path: str, dpi: int = 150):
    """Render PDF pages to images for the Input Viewer (frontend Pane 1).

    Requires Poppler (pdftoppm/pdftocairo) on PATH — this is an OS-level
    binary, not a pip package. As of the last check it is NOT installed on
    this dev machine (raises pdf2image.exceptions.PDFInfoNotInstalledError).
    See STATUS.md before relying on this in a demo.
    """
    from pdf2image import convert_from_path

    return convert_from_path(path, dpi=dpi)


def extract_geometry(path: str) -> list[GeometryBlock]:
    """Entry point of the Geometry Layer — dispatches by file extension."""
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return parse_docx(path)
    if ext == ".xlsx":
        return parse_xlsx(path)
    if ext == ".pdf":
        return parse_pdf(path)
    raise ValueError(f"Unsupported format for geometry extraction: {ext}")

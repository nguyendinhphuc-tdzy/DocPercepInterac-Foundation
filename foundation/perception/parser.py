"""Parse capability: Geometry Layer (deterministic, no AI).

Docling has been removed (decision confirmed 2026-08-11, per
Foundation_Build_Plan_v4.md mục 0 điểm 4 + STATUS.md) — replaced by
python-docx for DOCX and pdfplumber (+ pdf2image for page rendering) for
PDF. This is the "extract_geometry" step of the v3 pipeline:

    file_intake -> extract_geometry -> group_into_elements -> assign_anchors

group_into_elements/assign_anchors live in element_classifier.py /
anchor_builder.py (not yet built) — this module only produces raw geometry
blocks, one per paragraph/table-cell (DOCX) or text line (PDF), in document
order. No classification, no AI.
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
    row_index: Optional[int]
    col_index: Optional[int]
    # PDF fields
    page: Optional[int]
    bbox: Optional[tuple[float, float, float, float]]  # (x0, top, x1, bottom), pt


def parse_docx(path: str) -> list[GeometryBlock]:
    """Deterministic DOCX geometry via python-docx.

    One block per non-empty paragraph (in body order) plus one block per
    non-empty table cell, tagged with the same indices AnchorDOCX expects
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
                "row_index": None,
                "col_index": None,
                "page": None,
                "bbox": None,
            }
        )

    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                if not cell.text.strip():
                    continue
                blocks.append(
                    {
                        "text": cell.text,
                        "paragraph_index": None,
                        "style_id": None,
                        "table_index": t_idx,
                        "row_index": r_idx,
                        "col_index": c_idx,
                        "page": None,
                        "bbox": None,
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
                    }
                )
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
    if ext == ".pdf":
        return parse_pdf(path)
    raise ValueError(f"Unsupported format for geometry extraction: {ext}")

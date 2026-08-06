"""Unit tests for perception/models.py (P1-01 acceptance criteria)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.models import (
    BoundingBox,
    DocxAnchor,
    ElementType,
    FoundationDocument,
    FoundationElement,
    PdfAnchor,
    XlsxAnchor,
)


def test_docx_anchor_model_dump_json_is_valid_json():
    anchor = DocxAnchor(paragraph_index=5, style_id="Heading 1", text_fingerprint="a3f2b1c0")
    dumped = anchor.model_dump_json()
    parsed = json.loads(dumped)
    assert parsed["format"] == "docx"
    assert parsed["paragraph_index"] == 5


def test_xlsx_anchor_roundtrip():
    anchor = XlsxAnchor(sheet_name="BCTC", cell_address="B5")
    parsed = json.loads(anchor.model_dump_json())
    assert parsed["format"] == "xlsx"
    assert parsed["cell_address"] == "B5"


def test_pdf_anchor_bbox_bounds():
    anchor = PdfAnchor(
        page=1,
        bbox=BoundingBox(page=1, x=0.1, y=0.2, w=0.8, h=0.05),
        reading_order_index=3,
    )
    assert anchor.page == 1
    assert 0.0 <= anchor.bbox.x <= 1.0


def test_anchor_union_discriminates_by_format():
    docx_el = FoundationElement(
        type=ElementType.HEADING,
        text="A. CURRENT ASSETS",
        anchor=DocxAnchor(paragraph_index=0, style_id="Heading 1", text_fingerprint="abc123"),
    )
    xlsx_el = FoundationElement(
        type=ElementType.TABLE_CELL,
        text="1000000",
        anchor=XlsxAnchor(sheet_name="Sheet1", cell_address="A1"),
    )
    pdf_el = FoundationElement(
        type=ElementType.PARAGRAPH,
        text="Footnote",
        anchor=PdfAnchor(
            page=2,
            bbox=BoundingBox(page=2, x=0.0, y=0.0, w=1.0, h=1.0),
            reading_order_index=0,
        ),
    )

    assert isinstance(docx_el.anchor, DocxAnchor)
    assert isinstance(xlsx_el.anchor, XlsxAnchor)
    assert isinstance(pdf_el.anchor, PdfAnchor)

    # Round-trip through JSON must preserve the correct anchor subtype.
    doc = FoundationDocument(
        source_path="fixture_bcdt.docx",
        format="docx",
        page_count=1,
        elements=[docx_el, xlsx_el, pdf_el],
        docling_version="0.0.0-test",
    )
    reloaded = FoundationDocument.model_validate_json(doc.model_dump_json())
    assert isinstance(reloaded.elements[0].anchor, DocxAnchor)
    assert isinstance(reloaded.elements[1].anchor, XlsxAnchor)
    assert isinstance(reloaded.elements[2].anchor, PdfAnchor)


def test_confidence_bounds():
    el = FoundationElement(
        type=ElementType.PARAGRAPH,
        text="x",
        anchor=DocxAnchor(paragraph_index=0, style_id=None, text_fingerprint="ffffffff"),
        confidence=0.5,
    )
    assert 0.0 <= el.confidence <= 1.0

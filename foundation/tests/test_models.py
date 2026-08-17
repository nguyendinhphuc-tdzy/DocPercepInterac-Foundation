"""Unit tests for perception/models.py — schema per Foundation_Build_Plan.md section 3."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.models import (
    AnchorDOCX,
    AnchorPDF,
    AnchorXLSX,
    Element,
    ElementIndex,
    ElementType,
    Profile,
    ProfileField,
)


def test_docx_anchor_model_dump_json_is_valid_json():
    anchor = AnchorDOCX(paragraph_index=5, style_id="Heading 1", text_fingerprint="a3f2b1c0")
    dumped = anchor.model_dump_json()
    parsed = json.loads(dumped)
    assert parsed["format"] == "docx"
    assert parsed["paragraph_index"] == 5


def test_xlsx_anchor_roundtrip():
    anchor = AnchorXLSX(sheet_name="BCTC", cell_address="B5")
    parsed = json.loads(anchor.model_dump_json())
    assert parsed["format"] == "xlsx"
    assert parsed["cell_address"] == "B5"


def test_pdf_anchor_bbox_relative_bounds():
    anchor = AnchorPDF(page=1, bbox_relative=(0.1, 0.2, 0.8, 0.05), reading_order_index=3)
    assert anchor.page == 1
    assert all(0.0 <= v <= 1.0 for v in anchor.bbox_relative)


def test_anchor_union_discriminates_by_format():
    docx_el = Element(
        index=0,
        type=ElementType.HEADING,
        name="A. CURRENT ASSETS",
        anchor=AnchorDOCX(paragraph_index=0, style_id="Heading 1", text_fingerprint="abc123"),
    )
    xlsx_el = Element(
        index=1,
        type=ElementType.CELL,
        name="Revenue 2025",
        anchor=AnchorXLSX(sheet_name="Sheet1", cell_address="A1"),
    )
    pdf_el = Element(
        index=2,
        type=ElementType.PARA,
        name="Footnote",
        anchor=AnchorPDF(page=2, bbox_relative=(0.0, 0.0, 1.0, 1.0), reading_order_index=0),
    )

    assert isinstance(docx_el.anchor, AnchorDOCX)
    assert isinstance(xlsx_el.anchor, AnchorXLSX)
    assert isinstance(pdf_el.anchor, AnchorPDF)

    # Round-trip through JSON must preserve the correct anchor subtype.
    index = ElementIndex(
        source_path="fixture_bcdt.docx",
        format="docx",
        elements=[docx_el, xlsx_el, pdf_el],
    )
    reloaded = ElementIndex.model_validate_json(index.model_dump_json())
    assert isinstance(reloaded.elements[0].anchor, AnchorDOCX)
    assert isinstance(reloaded.elements[1].anchor, AnchorXLSX)
    assert isinstance(reloaded.elements[2].anchor, AnchorPDF)


def test_confidence_bounds():
    el = Element(
        index=0,
        type=ElementType.PARA,
        name="x",
        anchor=AnchorDOCX(paragraph_index=0, style_id="Normal", text_fingerprint="ffffffff"),
        confidence=0.5,
    )
    assert 0.0 <= el.confidence <= 1.0


def test_element_type_has_no_glossary_member():
    assert "GLOSSARY" not in ElementType.__members__
    assert "glossary" not in {member.value for member in ElementType}


def test_element_tags_roundtrip():
    el = Element(
        index=0,
        type=ElementType.PARA,
        name="Terms",
        anchor=AnchorDOCX(paragraph_index=0, style_id="Normal", text_fingerprint="abcd1234"),
        tags=["glossary"],
    )
    reloaded = Element.model_validate_json(el.model_dump_json())
    assert reloaded.tags == ["glossary"]


def test_profile_field_and_version():
    profile = Profile(
        profile_id="cit-workpaper-v1",
        version=1,
        document_type="bcdt",
        fields=[
            ProfileField(
                field_name="revenue",
                match_rule="label",
                anchor_pattern={"text_contains": "Doanh thu"},
            )
        ],
    )
    assert profile.version == 1
    assert profile.fields[0].match_rule == "label"

"""Unit tests for perception/element_classifier.py — the "See" step.

Uses the generic, non-financial fixture (tests/fixtures/fixture_generic_handbook.docx,
see tests/fixtures/_generate_generic_docx.py / tests/test_parser_generic.py) so
these assertions stay structural — valid for any DOCX, not specific to any
use case — matching the point of this module (generic, use-case-agnostic
classification).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.anchor_builder import assign_anchors
from perception.element_classifier import Classifier, classify_block, classify_blocks
from perception.models import Element, ElementType
from perception.parser import parse_docx

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fixture_generic_handbook.docx"


def _load():
    blocks = parse_docx(str(FIXTURE))
    anchors = assign_anchors(blocks, "docx")
    return blocks, anchors


def test_classify_blocks_returns_one_element_per_block_with_anchors():
    blocks, anchors = _load()
    elements = classify_blocks(blocks, "docx", anchors)

    assert len(elements) == len(blocks) == len(anchors)
    for el, anchor in zip(elements, anchors):
        assert isinstance(el, Element)
        assert el.anchor == anchor


def test_headings_classified_as_heading():
    blocks, anchors = _load()
    elements = classify_blocks(blocks, "docx", anchors)

    heading_elements = [el for el in elements if el.type == ElementType.HEADING]
    # fixture_generic_handbook.docx has 4 headings — see _generate_generic_docx.HEADINGS
    assert len(heading_elements) == 4
    for el in heading_elements:
        assert el.anchor.format == "docx"
        assert el.anchor.style_id.lower().startswith("heading")


def test_content_paragraphs_classified_as_para():
    blocks, anchors = _load()
    elements = classify_blocks(blocks, "docx", anchors)

    para_elements = [el for el in elements if el.type == ElementType.PARA]
    # fixture_generic_handbook.docx has 4 content paragraphs — see
    # _generate_generic_docx.PARAGRAPHS
    assert len(para_elements) == 4


def test_table_cells_classified_as_cell():
    blocks, anchors = _load()
    elements = classify_blocks(blocks, "docx", anchors)

    cell_elements = [el for el in elements if el.type == ElementType.CELL]
    # fixture_generic_handbook.docx has a 3x3 table — see
    # _generate_generic_docx.TABLE_ROWS
    assert len(cell_elements) == 9
    for el in cell_elements:
        assert el.anchor.format == "docx"
        assert el.anchor.table_index is not None
        assert el.anchor.row_index is not None
        assert el.anchor.col_index is not None


def test_classify_blocks_start_index_offsets_element_index():
    blocks, anchors = _load()
    elements = classify_blocks(blocks, "docx", anchors, start_index=100)

    assert [el.index for el in elements] == list(range(100, 100 + len(blocks)))


def test_classify_block_matches_classify_blocks_element_by_element():
    blocks, anchors = _load()
    via_blocks = classify_blocks(blocks, "docx", anchors)
    via_single = [
        classify_block(b, i, "docx", a) for i, (b, a) in enumerate(zip(blocks, anchors))
    ]
    assert via_blocks == via_single


def test_classify_blocks_satisfies_the_document_level_classifier_protocol():
    """classify_blocks is the baseline Classifier — its signature must match
    the document-level Protocol exactly: all blocks/anchors of a document in
    one call, not one block at a time.
    """
    baseline: Classifier = classify_blocks
    blocks, anchors = _load()
    elements = baseline(blocks, "docx", anchors)
    assert isinstance(elements, list)
    assert len(elements) == len(blocks)


def test_document_level_classifier_is_a_drop_in_replacement_for_the_baseline():
    """Demonstrates the document-level seam: a caller holds a `Classifier`
    reference (defaulting to classify_blocks) and invokes it uniformly. A
    different implementation matching the same (blocks, fmt, anchors,
    start_index) signature — e.g. a future AI-model wrapper with access to
    every block at once — is a drop-in replacement, with no dispatcher or
    per-block parameter involved.
    """
    blocks, anchors = _load()

    def mock_document_classifier(
        blocks, fmt, anchors, start_index: int = 0
    ) -> list[Element]:
        # A real AI implementation would use cross-block context here (e.g.
        # all blocks at once) — this mock just proves the call shape works
        # and that the caller's choice of Classifier is actually honored.
        return [
            Element(
                index=start_index + i,
                type=ElementType.PARA,
                name=f"mock-classified (saw {len(blocks)} blocks total)",
                text=block.get("text") or "",
                anchor=anchor,
                confidence=0.0,
            )
            for i, (block, anchor) in enumerate(zip(blocks, anchors))
        ]

    def run_with(classifier: Classifier) -> list[Element]:
        return classifier(blocks, "docx", anchors)

    baseline_elements = run_with(classify_blocks)
    mock_elements = run_with(mock_document_classifier)

    assert len(mock_elements) == len(blocks)
    assert all(el.type == ElementType.PARA for el in mock_elements)
    assert all(str(len(blocks)) in el.name for el in mock_elements)

    # sanity check: the baseline would NOT have classified everything as
    # PARA (the fixture has headings and table cells too), proving the
    # mock classifier was actually used in place of the baseline, not
    # silently ignored.
    baseline_types = {el.type for el in baseline_elements}
    assert baseline_types != {ElementType.PARA}

"""Genericity regression guard for perception/parser.py.

Every other DOCX fixture in this repo (fixture_bcdt.docx) is a real
financial statement — parsing only that leaves "the Geometry Layer is
generic, not financial-statement-shaped" an unverified claim.
fixture_generic_handbook.docx (tests/fixtures/_generate_generic_docx.py) is
a wholly fictional, non-financial document with the same *structural*
shape (headings, prose paragraphs, a table), so this test can assert the
same structural properties any digital DOCX should satisfy, without
touching financial content at all.

Keep assertions structural only — do NOT add anything here that would only
hold for financial documents (that would defeat the point of this file).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.parser import extract_geometry, parse_docx

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE = FIXTURES / "fixture_generic_handbook.docx"

# Load the generator module by path (not via package import) so the fixture
# content/structure lives in exactly one place and these tests can't drift
# from what tests/fixtures/_generate_generic_docx.py actually produced.
_spec = importlib.util.spec_from_file_location(
    "_generate_generic_docx", FIXTURES / "_generate_generic_docx.py"
)
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)
HEADINGS = _gen.HEADINGS
PARAGRAPHS = _gen.PARAGRAPHS
TABLE_ROWS = _gen.TABLE_ROWS


def test_fixture_exists():
    assert FIXTURE.exists(), (
        "fixture_generic_handbook.docx is missing — regenerate it with "
        "python tests/fixtures/_generate_generic_docx.py"
    )


def test_parse_docx_returns_blocks():
    blocks = parse_docx(str(FIXTURE))
    assert isinstance(blocks, list)
    assert len(blocks) > 0


def test_headings_detected_with_style_id():
    blocks = parse_docx(str(FIXTURE))
    heading_texts = {text for _level, text in HEADINGS}
    heading_blocks = [b for b in blocks if b["text"] in heading_texts]

    assert len(heading_blocks) == len(HEADINGS)
    for b in heading_blocks:
        assert b["style_id"] is not None
        assert b["style_id"].startswith("Heading")

    # all 3 distinct heading levels used in the fixture are represented
    style_ids = {b["style_id"] for b in heading_blocks}
    assert style_ids == {f"Heading{level}" for level, _text in HEADINGS}


def test_content_paragraphs_preserved():
    blocks = parse_docx(str(FIXTURE))
    texts = {b["text"] for b in blocks}
    for expected in PARAGRAPHS:
        assert expected in texts


def test_table_detected_with_correct_dimensions_and_cell_data():
    blocks = parse_docx(str(FIXTURE))
    cell_blocks = [b for b in blocks if b["table_index"] is not None]

    n_rows = len(TABLE_ROWS)
    n_cols = len(TABLE_ROWS[0])
    assert len(cell_blocks) == n_rows * n_cols

    # single table, single index shared by every cell block
    table_indices = {b["table_index"] for b in cell_blocks}
    assert len(table_indices) == 1

    by_position = {(b["row_index"], b["col_index"]): b["text"] for b in cell_blocks}
    for r, row_values in enumerate(TABLE_ROWS):
        for c, value in enumerate(row_values):
            assert by_position[(r, c)] == value


def test_extract_geometry_dispatches_to_parse_docx_for_generic_fixture():
    assert extract_geometry(str(FIXTURE)) == parse_docx(str(FIXTURE))

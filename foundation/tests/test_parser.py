"""Unit tests for perception/parser.py (P1-03 acceptance criteria)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.parser import get_converter, parse_document

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_document_returns_dict_with_elements():
    doc = parse_document(str(FIXTURES / "fixture_bcdt.docx"))
    assert isinstance(doc, dict)
    assert "texts" in doc or "body" in doc  # DoclingDocument export shape


def test_converter_is_singleton():
    c1 = get_converter()
    c2 = get_converter()
    assert c1 is c2


def test_parse_docx_under_60s_cpu():
    start = time.monotonic()
    parse_document(str(FIXTURES / "fixture_bcdt.docx"))
    elapsed = time.monotonic() - start
    assert elapsed < 60, f"Parse took {elapsed:.1f}s, exceeds 60s CPU budget"


def test_parse_pdf_does_not_crash():
    doc = parse_document(str(FIXTURES / "fixture_report.pdf"))
    assert isinstance(doc, dict)

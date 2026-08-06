"""Unit tests for perception/detector.py (P1-02 acceptance criteria)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.detector import detect_format

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_detect_docx():
    result = detect_format(str(FIXTURES / "fixture_bcdt.docx"))
    assert result["format"] == "docx"
    assert result["size"] > 0


def test_detect_pdf():
    result = detect_format(str(FIXTURES / "fixture_report.pdf"))
    assert result["format"] == "pdf"
    assert result["mime"] == "application/pdf"


def test_detect_unsupported_extension_raises_clear_error(tmp_path):
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("plain text file")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        detect_format(str(unsupported))


def test_detect_missing_file_raises():
    with pytest.raises(ValueError, match="File not found"):
        detect_format(str(FIXTURES / "does_not_exist.docx"))

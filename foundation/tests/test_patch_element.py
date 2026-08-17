"""Tests for the live-edit path: WritebackEngine.apply_single_patch()
(mapping/writeback.py) and PATCH /api/elements/<process_id>
(api/routes/process.py) — writes a new value directly into the output
document at an element's Anchor, without re-running the full pipeline.
"""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docx import Document as DocxDocument  # noqa: E402

from perception.anchor_builder import assign_docx_anchor  # noqa: E402
from perception.parser import parse_docx  # noqa: E402
from mapping.writeback import WritebackEngine  # noqa: E402

# --- WritebackEngine.apply_single_patch() — unit level -----------------------


def test_apply_single_patch_docx_paragraph(tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Original text.")
    path = tmp_path / "doc.docx"
    doc.save(path)

    blocks = parse_docx(str(path))
    anchor = assign_docx_anchor(blocks[0])

    output_path = tmp_path / "patched.docx"
    message = WritebackEngine().apply_single_patch(str(path), anchor, "Edited text.", str(output_path))

    assert message is None
    reopened = DocxDocument(str(output_path))
    assert reopened.paragraphs[0].text == "Edited text."


def test_apply_single_patch_docx_table_cell(tmp_path):
    doc = DocxDocument()
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Header"
    table.rows[1].cells[0].text = "Old value"
    path = tmp_path / "doc.docx"
    doc.save(path)

    blocks = parse_docx(str(path))
    cell_block = next(b for b in blocks if b["text"] == "Old value")
    anchor = assign_docx_anchor(cell_block)

    output_path = tmp_path / "patched.docx"
    WritebackEngine().apply_single_patch(str(path), anchor, "New value", str(output_path))

    reopened = DocxDocument(str(output_path))
    assert reopened.tables[0].rows[1].cells[0].text == "New value"


def test_apply_single_patch_accumulates_across_multiple_edits(tmp_path):
    """The PATCH route re-uses the same output path as both input and
    output on the second+ edit — confirm that read-modify-write pattern
    doesn't lose the first edit."""
    doc = DocxDocument()
    doc.add_paragraph("Para one.")
    doc.add_paragraph("Para two.")
    path = tmp_path / "doc.docx"
    doc.save(path)

    blocks = parse_docx(str(path))
    anchor_one = assign_docx_anchor(blocks[0])
    anchor_two = assign_docx_anchor(blocks[1])

    output_path = tmp_path / "patched.docx"
    engine = WritebackEngine()
    engine.apply_single_patch(str(path), anchor_one, "Edited one.", str(output_path))
    engine.apply_single_patch(str(output_path), anchor_two, "Edited two.", str(output_path))

    reopened = DocxDocument(str(output_path))
    assert reopened.paragraphs[0].text == "Edited one."
    assert reopened.paragraphs[1].text == "Edited two."


def test_apply_single_patch_rejects_pdf_anchor(tmp_path):
    from perception.models import AnchorPDF

    anchor = AnchorPDF(page=1, bbox_relative=(0, 0, 1, 1), reading_order_index=0)
    with pytest.raises(ValueError):
        WritebackEngine().apply_single_patch("irrelevant.pdf", anchor, "x", "irrelevant_out.pdf")


# --- PATCH /api/elements/<process_id> — route level ---------------------------


@pytest.fixture
def client(monkeypatch, tmp_path):
    import api.routes.process as process_module
    from api.app import create_app

    monkeypatch.setattr(process_module, "UPLOAD_ROOT", tmp_path)
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _seed_process_dir(tmp_path, process_id, doc):
    process_dir = tmp_path / process_id
    process_dir.mkdir(parents=True)
    target_path = process_dir / "target.docx"
    doc.save(target_path)
    return process_dir, target_path


def test_patch_element_seeds_patched_file_from_target_when_none_exists(client, tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Original text.")
    process_id = str(uuid.uuid4())
    process_dir, target_path = _seed_process_dir(tmp_path, process_id, doc)

    blocks = parse_docx(str(target_path))
    anchor = assign_docx_anchor(blocks[0])

    response = client.patch(
        f"/api/elements/{process_id}",
        json={"anchor": anchor.model_dump(mode="json"), "value": "Edited via UI."},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["download_url"] == f"/api/download/{process_id}"

    patched_path = process_dir / "target_patched.docx"
    assert patched_path.exists()
    assert DocxDocument(str(patched_path)).paragraphs[0].text == "Edited via UI."
    # Original target must be left untouched.
    assert DocxDocument(str(target_path)).paragraphs[0].text == "Original text."


def test_patch_element_edits_accumulate_on_existing_patched_file(client, tmp_path):
    doc = DocxDocument()
    doc.add_paragraph("Para one.")
    doc.add_paragraph("Para two.")
    process_id = str(uuid.uuid4())
    process_dir, target_path = _seed_process_dir(tmp_path, process_id, doc)

    blocks = parse_docx(str(target_path))
    anchor_one = assign_docx_anchor(blocks[0])
    anchor_two = assign_docx_anchor(blocks[1])

    r1 = client.patch(
        f"/api/elements/{process_id}",
        json={"anchor": anchor_one.model_dump(mode="json"), "value": "First edit."},
    )
    assert r1.status_code == 200

    r2 = client.patch(
        f"/api/elements/{process_id}",
        json={"anchor": anchor_two.model_dump(mode="json"), "value": "Second edit."},
    )
    assert r2.status_code == 200

    patched = DocxDocument(str(process_dir / "target_patched.docx"))
    assert patched.paragraphs[0].text == "First edit."  # not lost by the second edit
    assert patched.paragraphs[1].text == "Second edit."


def test_patch_element_returns_404_for_unknown_process_id(client):
    response = client.patch(
        "/api/elements/does-not-exist",
        json={"anchor": {"format": "docx", "style_id": "", "text_fingerprint": "abcd1234"}, "value": "x"},
    )
    assert response.status_code == 404


def test_patch_element_returns_400_for_missing_body(client, tmp_path):
    process_id = str(uuid.uuid4())
    doc = DocxDocument()
    doc.add_paragraph("x")
    _seed_process_dir(tmp_path, process_id, doc)

    response = client.patch(f"/api/elements/{process_id}", json={"anchor": {"format": "docx"}})
    assert response.status_code == 400


def test_patch_element_returns_400_for_malformed_anchor(client, tmp_path):
    process_id = str(uuid.uuid4())
    doc = DocxDocument()
    doc.add_paragraph("x")
    _seed_process_dir(tmp_path, process_id, doc)

    # Missing required fields (sheet_name, cell_address) — fails pydantic
    # validation before the format check ever runs.
    response = client.patch(
        f"/api/elements/{process_id}",
        json={"anchor": {"format": "xlsx"}, "value": "y"},
    )
    assert response.status_code == 400


def test_patch_element_returns_400_for_unsupported_output_format(client, tmp_path):
    process_id = str(uuid.uuid4())
    doc = DocxDocument()
    doc.add_paragraph("x")
    _seed_process_dir(tmp_path, process_id, doc)

    # Well-formed AnchorXLSX — passes validation, rejected because only
    # DOCX output is wired up for editing.
    response = client.patch(
        f"/api/elements/{process_id}",
        json={
            "anchor": {"format": "xlsx", "sheet_name": "Sheet1", "cell_address": "A1"},
            "value": "y",
        },
    )
    assert response.status_code == 400

"""Tests for the generic document layer:
  - POST /api/documents (api/routes/documents.py) — upload + Perceive, one
    document per call, no role inference, no GTPS vocabulary anywhere in
    the response.
  - GET /api/documents/<session_id> — session document listing.
  - GET /api/documents/<session_id>/elements/<doc_id> — lazy element fetch.
  - POST /api/gpts/map (api/routes/gpts.py) — the GTPS-specific mapping
    execution, only ever triggered by an explicit call with explicit
    source/target doc_ids, never by uploading.

Uses fixture_generic_handbook.docx (tests/fixtures/_generate_generic_docx.py)
for the generic-route tests so assertions stay structural, not financial —
consistent with tests/test_parser_generic.py / test_element_classifier.py.
"""
import io
import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIXTURE_GENERIC_DOCX = Path(__file__).resolve().parent / "fixtures" / "fixture_generic_handbook.docx"
FIXTURE_PDF = Path(__file__).resolve().parent / "fixtures" / "fixture_report_2.pdf"

DEMO_ROOT = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
SOURCE_XLSX = DEMO_ROOT / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"
TARGET_DOCX = DEMO_ROOT / "Compare LF" / "HMV-26-Final-Local File for FY2024-EN-R2901KPMG_drifted.docx"
requires_demo_fixtures = pytest.mark.skipif(
    not (SOURCE_XLSX.exists() and TARGET_DOCX.exists()),
    reason="HMV demo fixture files not present on this machine",
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    import api.routes.documents as documents_module
    from api.app import create_app

    monkeypatch.setattr(documents_module, "UPLOAD_ROOT", tmp_path)
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _upload(client, path: Path, session_id: str | None = None):
    data = {"file": (io.BytesIO(path.read_bytes()), path.name)}
    if session_id:
        data["session_id"] = session_id
    return client.post("/api/documents", data=data, content_type="multipart/form-data")


def test_upload_document_perceives_and_returns_generic_summary(client):
    response = _upload(client, FIXTURE_GENERIC_DOCX)
    assert response.status_code == 200
    body = response.get_json()

    assert body["status"] == "ready"
    assert body["error"] is None
    assert body["format"] == "docx"
    assert body["filename"] == FIXTURE_GENERIC_DOCX.name
    assert body["element_count"] > 0
    assert "session_id" in body and "doc_id" in body


def test_upload_response_contains_no_gtps_vocabulary(client):
    """Regression guard for the architectural invariant: the generic
    document layer must never expose source/target/mapping concepts —
    those belong entirely to api/routes/gpts.py."""
    response = _upload(client, FIXTURE_GENERIC_DOCX)
    body = response.get_json()

    raw = json.dumps(body).lower()
    forbidden_terms = [
        "source_elements", "target_elements", "\"mapped\"", "mapping",
        "\"source\"", "\"target\"", "gtps", "hmv", "demo_rules",
    ]
    for term in forbidden_terms:
        assert term not in raw, f"generic /api/documents response leaked GTPS vocabulary: {term!r}"


def test_upload_rejects_unsupported_format(client, tmp_path):
    bogus = tmp_path / "notes.txt"
    bogus.write_text("hello")
    response = _upload(client, bogus)
    assert response.status_code == 400
    assert "Unsupported format" in response.get_json()["error"]


def test_second_upload_with_same_session_id_accumulates_documents(client):
    r1 = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = r1.get_json()["session_id"]

    r2 = _upload(client, FIXTURE_GENERIC_DOCX, session_id=session_id)
    assert r2.get_json()["session_id"] == session_id

    listing = client.get(f"/api/documents/{session_id}")
    assert listing.status_code == 200
    docs = listing.get_json()["documents"]
    assert len(docs) == 2
    # doc_ids are stable, distinct identities — never derived from upload
    # order/filename/position.
    assert docs[0]["doc_id"] != docs[1]["doc_id"]


def test_three_arbitrary_formats_share_one_session_with_independent_status(client, tmp_path):
    """The explicit multi-file session-lifecycle acceptance scenario: a PDF,
    an XLSX, and a DOCX — uploaded one at a time, each joining the session
    established by the first — must all end up addressable under the SAME
    session_id, each with its own independent status, in NO particular
    role or order. This is the scenario
    frontend/src/state/workspaceStore.ts's `pendingSessionPromise`
    specifically exists to guarantee client-side (a real concurrency bug —
    two uploads racing before either had a session_id, landing in two
    separate sessions — was caught via a live browser run and fixed
    there); this test locks down the SERVER half of that contract: passing
    the session_id back always joins the same session, regardless of
    upload order or format mix.
    """
    import openpyxl

    wb = openpyxl.Workbook()
    wb.active.title = "Notes"
    wb.active["A1"] = "Volunteer shift log"  # deliberately non-financial
    xlsx_bytes = io.BytesIO()
    wb.save(xlsx_bytes)
    xlsx_bytes.seek(0)

    # 1) DOCX first — establishes the session.
    docx_resp = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = docx_resp.get_json()["session_id"]
    docx_doc_id = docx_resp.get_json()["doc_id"]

    # 2) XLSX second — must explicitly join the same session.
    xlsx_resp = client.post(
        "/api/documents",
        data={"file": (xlsx_bytes, "notes.xlsx"), "session_id": session_id},
        content_type="multipart/form-data",
    )
    xlsx_doc_id = xlsx_resp.get_json()["doc_id"]
    assert xlsx_resp.get_json()["session_id"] == session_id

    # 3) PDF third — same requirement.
    pdf_resp = _upload(client, FIXTURE_PDF, session_id=session_id)
    pdf_doc_id = pdf_resp.get_json()["doc_id"]
    assert pdf_resp.get_json()["session_id"] == session_id

    # All three land in exactly one session, each with a distinct doc_id.
    listing = client.get(f"/api/documents/{session_id}").get_json()
    docs_by_id = {d["doc_id"]: d for d in listing["documents"]}
    assert set(docs_by_id) == {docx_doc_id, xlsx_doc_id, pdf_doc_id}
    assert len(docs_by_id) == 3  # no accidental merging/collision either

    # Independent status per document, independent format, no role field
    # anywhere in the listing.
    assert docs_by_id[docx_doc_id]["format"] == "docx"
    assert docs_by_id[xlsx_doc_id]["format"] == "xlsx"
    assert docs_by_id[pdf_doc_id]["format"] == "pdf"
    assert all(d["status"] == "ready" for d in docs_by_id.values())
    raw = json.dumps(listing).lower()
    for forbidden in ("source", "target", "mapped", "mapping", "gtps", "hmv"):
        assert forbidden not in raw

    # Each document's elements are independently addressable by its own
    # doc_id, regardless of upload order.
    for doc_id in (pdf_doc_id, docx_doc_id, xlsx_doc_id):  # deliberately out of upload order
        elements_resp = client.get(f"/api/documents/{session_id}/elements/{doc_id}")
        assert elements_resp.status_code == 200
        assert len(elements_resp.get_json()["elements"]) == docs_by_id[doc_id]["element_count"]

    # An explicit application action can reference any combination of this
    # session's doc_ids — addressability doesn't depend on upload order or
    # on which formats were involved. (DEMO_RULES won't match this
    # content, so `mapped` is expected to be empty — the point here is
    # that the doc_ids resolve at all, not that they map to anything.)
    map_resp = client.post(
        "/api/gpts/map",
        json={
            "session_id": session_id,
            "source_doc_ids": [xlsx_doc_id, pdf_doc_id],
            "target_doc_id": docx_doc_id,
        },
    )
    assert map_resp.status_code == 200
    assert map_resp.get_json()["mapped"] == []


def test_failed_upload_does_not_affect_other_documents_in_the_session(client, tmp_path):
    """Each document's status is independent — one failing upload must not
    affect another document already marked ready in the same session (no
    shared mutable "workspace processing" flag exists to race on)."""
    good = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = good.get_json()["session_id"]
    good_doc_id = good.get_json()["doc_id"]

    bogus = tmp_path / "notes.txt"
    bogus.write_text("hello")
    bad = _upload(client, bogus, session_id=session_id)
    assert bad.status_code == 400  # rejected before a doc_id is even minted

    listing = client.get(f"/api/documents/{session_id}").get_json()
    assert len(listing["documents"]) == 1
    assert listing["documents"][0]["doc_id"] == good_doc_id
    assert listing["documents"][0]["status"] == "ready"


def test_get_document_elements_is_lazy_and_matches_upload_count(client):
    upload = _upload(client, FIXTURE_GENERIC_DOCX)
    body = upload.get_json()
    session_id, doc_id = body["session_id"], body["doc_id"]

    elements_response = client.get(f"/api/documents/{session_id}/elements/{doc_id}")
    assert elements_response.status_code == 200
    elements = elements_response.get_json()["elements"]
    assert len(elements) == body["element_count"]
    # generic element shape only — no GTPS fields. `element_id`,
    # `parent_id`, and `capabilities` were added by the Comprehensive
    # Document Perception phase (stable identity + detected/extracted/
    # rendered/selectable/editable metadata) — still no GTPS-shaped fields.
    assert set(elements[0].keys()) <= {
        "index", "element_id", "parent_id", "section", "type", "name", "text", "text_normalized",
        "source", "anchor", "confidence", "tags", "capabilities",
    }


def test_get_elements_returns_404_for_unknown_doc_id(client):
    upload = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = upload.get_json()["session_id"]
    response = client.get(f"/api/documents/{session_id}/elements/{uuid.uuid4()}")
    assert response.status_code == 404


def test_list_documents_returns_404_for_unknown_session(client):
    response = client.get("/api/documents/does-not-exist")
    assert response.status_code == 404


# --- POST /api/gpts/map — explicit, application-scoped execution ------------


@requires_demo_fixtures
def test_gpts_map_requires_explicit_invocation_and_reproduces_demo_result(client):
    """Uploading the exact same HMV source+target pair must NOT trigger any
    mapping on its own — only an explicit POST /api/gpts/map call with
    explicit doc_ids does. When it is called, it must still reproduce the
    same 3-mapped HMV demo result as applications/gpts/mapping_service.py's
    own direct-call tests (test_mapping_service.py) — proving the route
    split didn't change run_mapping's behavior."""
    source_upload = _upload(client, SOURCE_XLSX)
    session_id = source_upload.get_json()["session_id"]
    source_doc_id = source_upload.get_json()["doc_id"]

    target_upload = _upload(client, TARGET_DOCX, session_id=session_id)
    target_doc_id = target_upload.get_json()["doc_id"]

    # Perceiving both documents must not have produced any mapping.
    listing = client.get(f"/api/documents/{session_id}").get_json()
    assert all(d["status"] == "ready" for d in listing["documents"])

    response = client.post(
        "/api/gpts/map",
        json={
            "session_id": session_id,
            "source_doc_ids": [source_doc_id],
            "target_doc_id": target_doc_id,
        },
    )
    assert response.status_code == 200
    body = response.get_json()

    assert len(body["mapped"]) == 3
    mapped_source_anchors = {m["source_anchor"] for m in body["mapped"]}
    assert mapped_source_anchors == {"RPTs!E8", "RPTs!F8", "Financial Analysis!D7"}
    assert body["download_url"] == f"/api/documents/{session_id}/download/{target_doc_id}"

    download = client.get(body["download_url"])
    assert download.status_code == 200


def test_gpts_map_returns_400_when_roles_missing(client):
    upload = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = upload.get_json()["session_id"]

    response = client.post("/api/gpts/map", json={"session_id": session_id})
    assert response.status_code == 400


def test_gpts_map_returns_404_for_unknown_doc_ids(client):
    upload = _upload(client, FIXTURE_GENERIC_DOCX)
    session_id = upload.get_json()["session_id"]

    response = client.post(
        "/api/gpts/map",
        json={
            "session_id": session_id,
            "source_doc_ids": [str(uuid.uuid4())],
            "target_doc_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 404

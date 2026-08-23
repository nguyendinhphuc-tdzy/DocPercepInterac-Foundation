"""
Multi-document intake is additive (P0 bug: a second upload erased the first).

The defect: assigning a file is read-modify-write — a new source changes the
verdicts of the OTHER slots too, so the whole slot set is written back. Two
overlapping uploads each loaded the state before the other had saved, and the
slower request's write pruned the faster one's assignment. The document itself
survived in storage; its slot assignment did not, so the file vanished from the
panel.

These tests pin the invariants that make that impossible:

    * uploading into CURRENT_YEAR_SOURCES appends, never replaces
    * uploading into one slot never touches another slot
    * concurrent uploads keep every assignment
    * one session never grows a second workflow_id
    * replacement happens only for an explicit single-file slot re-assignment
"""
from __future__ import annotations

import io
import sys
import threading
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

warnings.filterwarnings("ignore")

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_DOCX = FIXTURES / "fixture_generic_handbook.docx"
FIXTURE_PDF = FIXTURES / "fixture_report_2.pdf"
DEMO = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
HISTORICAL = DEMO / "Compare LF" / "HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx"
TEMPLATE = (DEMO / "Compare LF"
            / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 "
              "(Decree 20-2025).docx")
FA_RPT = DEMO / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"
APPENDIX_I = (DEMO / "FA&RPTS & Appendix I" / "Appendix I"
              / "HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx")

pytestmark = pytest.mark.skipif(
    not FIXTURE_DOCX.exists(), reason="generic docx fixture is not present")
requires_demo = pytest.mark.skipif(
    not HISTORICAL.exists(), reason="demo fixtures are not present")


@pytest.fixture
def client(monkeypatch, tmp_path):
    import adapters.repository as repository_module
    import api.routes.documents as documents_module
    import api.routes.workflow as workflow_module
    from adapters.repository import reset_repositories
    from api.app import create_app

    monkeypatch.setattr(documents_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(workflow_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(repository_module, "UPLOAD_ROOT", tmp_path)
    reset_repositories()

    app = create_app()
    app.config.update(TESTING=True)
    yield app
    reset_repositories()


def _upload(app, path: Path, session_id: str | None = None, user: str = "user-a"):
    data = {"file": (io.BytesIO(path.read_bytes()), path.name)}
    if session_id:
        data["session_id"] = session_id
    with app.test_client() as http:
        response = http.post("/api/documents", data=data,
                             content_type="multipart/form-data",
                             headers={"X-User-Id": user})
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _start(app, session_id: str, user: str = "user-a"):
    with app.test_client() as http:
        return http.post("/api/workflow/sessions",
                         json={"session_id": session_id, "workflow": "LOCAL_FILE_ROLL_FORWARD"},
                         headers={"X-User-Id": user})


def _assign(app, session_id: str, slot: str, doc_id: str, user: str = "user-a"):
    with app.test_client() as http:
        return http.post(f"/api/workflow/{session_id}/slots/{slot}/assign",
                         json={"doc_id": doc_id}, headers={"X-User-Id": user})


def _state(app, session_id: str, user: str = "user-a"):
    with app.test_client() as http:
        return http.get(f"/api/workflow/{session_id}", headers={"X-User-Id": user}).get_json()


def _documents(app, session_id: str, user: str = "user-a"):
    with app.test_client() as http:
        return http.get(f"/api/documents/{session_id}",
                        headers={"X-User-Id": user}).get_json()["documents"]


def _slots(payload: dict) -> dict:
    return {s["slot_id"]: list(s["assigned_document_ids"]) for s in payload["slots"]}


def _total_assigned(payload: dict) -> int:
    return sum(len(ids) for ids in _slots(payload).values())


# ---------------------------------------------------------------------------
# SEQUENTIAL: every upload adds one
# ---------------------------------------------------------------------------

@requires_demo
def test_each_upload_adds_a_document_and_keeps_the_previous_ones(client):
    first = _upload(client, HISTORICAL)
    session_id = first["session_id"]
    _start(client, session_id)
    _assign(client, session_id, "HISTORICAL_LOCAL_FILE", first["doc_id"])

    fa = _upload(client, FA_RPT, session_id)
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", fa["doc_id"])
    after_two = _state(client, session_id)
    assert _slots(after_two)["HISTORICAL_LOCAL_FILE"] == [first["doc_id"]], \
        "the historical file was dropped when a source was added"
    assert _slots(after_two)["CURRENT_YEAR_SOURCES"] == [fa["doc_id"]]
    assert len(_documents(client, session_id)) == 2

    appendix = _upload(client, APPENDIX_I, session_id)
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", appendix["doc_id"])
    after_three = _state(client, session_id)
    assert _slots(after_three)["HISTORICAL_LOCAL_FILE"] == [first["doc_id"]]
    assert _slots(after_three)["CURRENT_YEAR_SOURCES"] == [fa["doc_id"], appendix["doc_id"]]
    assert len(_documents(client, session_id)) == 3

    template = _upload(client, TEMPLATE, session_id)
    _assign(client, session_id, "MASTER_TEMPLATE", template["doc_id"])
    after_four = _state(client, session_id)
    assert _total_assigned(after_four) == 4
    assert _slots(after_four)["MASTER_TEMPLATE"] == [template["doc_id"]]
    assert len(_documents(client, session_id)) == 4


def test_a_second_source_appends_rather_than_replaces(client):
    first = _upload(client, FIXTURE_DOCX)
    session_id = first["session_id"]
    _start(client, session_id)
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", first["doc_id"])

    second = _upload(client, FIXTURE_PDF, session_id) if FIXTURE_PDF.exists() else None
    if second is None:
        pytest.skip("second fixture is not present")

    # A PDF is not an accepted source format, but the point stands: the earlier
    # assignment must still be there afterwards, whatever the verdict.
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", second["doc_id"])
    sources = _slots(_state(client, session_id))["CURRENT_YEAR_SOURCES"]
    assert first["doc_id"] in sources
    assert len(sources) == 2


# ---------------------------------------------------------------------------
# CONCURRENT: the actual bug
# ---------------------------------------------------------------------------

@requires_demo
def test_overlapping_uploads_into_different_slots_keep_both(client):
    """The reported repro: a source assigned while the historical one is in flight."""
    historical = _upload(client, HISTORICAL)
    session_id = historical["session_id"]
    fa = _upload(client, FA_RPT, session_id)
    _start(client, session_id)

    results = {}

    def assign(slot, doc_id):
        results[slot] = _assign(client, session_id, slot, doc_id).status_code

    threads = [
        threading.Thread(target=assign, args=("HISTORICAL_LOCAL_FILE", historical["doc_id"])),
        threading.Thread(target=assign, args=("CURRENT_YEAR_SOURCES", fa["doc_id"])),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=300)

    assert set(results.values()) == {200}, results
    slots = _slots(_state(client, session_id))
    assert slots["HISTORICAL_LOCAL_FILE"] == [historical["doc_id"]], \
        "the concurrent source assignment erased the historical assignment"
    assert slots["CURRENT_YEAR_SOURCES"] == [fa["doc_id"]], \
        "the concurrent historical assignment erased the source assignment"


@requires_demo
def test_concurrent_sources_all_survive(client):
    first = _upload(client, FA_RPT)
    session_id = first["session_id"]
    second = _upload(client, APPENDIX_I, session_id)
    _start(client, session_id)

    threads = [
        threading.Thread(target=_assign,
                         args=(client, session_id, "CURRENT_YEAR_SOURCES", doc["doc_id"]))
        for doc in (first, second)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=300)

    sources = _slots(_state(client, session_id))["CURRENT_YEAR_SOURCES"]
    assert sorted(sources) == sorted([first["doc_id"], second["doc_id"]])


def test_concurrent_workflow_creation_yields_one_workflow(client):
    """Two starts for one session must not mint two workflow_ids.

    Assignments are keyed by workflow_id, so a second one would orphan every
    slot written against the first.
    """
    uploaded = _upload(client, FIXTURE_DOCX)
    session_id = uploaded["session_id"]

    created = []

    def start():
        created.append(_start(client, session_id).get_json())

    threads = [threading.Thread(target=start) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    workflow_ids = {payload["workflow_id"] for payload in created}
    assert len(workflow_ids) == 1, f"session grew {len(workflow_ids)} workflows: {workflow_ids}"

    _assign(client, session_id, "CURRENT_YEAR_SOURCES", uploaded["doc_id"])
    assert _total_assigned(_state(client, session_id)) == 1


# ---------------------------------------------------------------------------
# REPLACEMENT IS EXPLICIT AND SCOPED
# ---------------------------------------------------------------------------

@requires_demo
def test_replacing_the_historical_file_leaves_the_sources_untouched(client):
    historical = _upload(client, HISTORICAL)
    session_id = historical["session_id"]
    fa = _upload(client, FA_RPT, session_id)
    appendix = _upload(client, APPENDIX_I, session_id)
    _start(client, session_id)
    _assign(client, session_id, "HISTORICAL_LOCAL_FILE", historical["doc_id"])
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", fa["doc_id"])
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", appendix["doc_id"])

    replacement = _upload(client, TEMPLATE, session_id)
    _assign(client, session_id, "HISTORICAL_LOCAL_FILE", replacement["doc_id"])

    slots = _slots(_state(client, session_id))
    assert slots["HISTORICAL_LOCAL_FILE"] == [replacement["doc_id"]]   # replaced
    assert slots["CURRENT_YEAR_SOURCES"] == [fa["doc_id"], appendix["doc_id"]]  # untouched


@requires_demo
def test_replacing_the_template_leaves_the_sources_untouched(client):
    template = _upload(client, TEMPLATE)
    session_id = template["session_id"]
    fa = _upload(client, FA_RPT, session_id)
    _start(client, session_id)
    _assign(client, session_id, "MASTER_TEMPLATE", template["doc_id"])
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", fa["doc_id"])

    replacement = _upload(client, HISTORICAL, session_id)
    _assign(client, session_id, "MASTER_TEMPLATE", replacement["doc_id"])

    slots = _slots(_state(client, session_id))
    assert slots["MASTER_TEMPLATE"] == [replacement["doc_id"]]
    assert slots["CURRENT_YEAR_SOURCES"] == [fa["doc_id"]]


@requires_demo
def test_removing_one_source_keeps_the_others(client):
    fa = _upload(client, FA_RPT)
    session_id = fa["session_id"]
    appendix = _upload(client, APPENDIX_I, session_id)
    _start(client, session_id)
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", fa["doc_id"])
    _assign(client, session_id, "CURRENT_YEAR_SOURCES", appendix["doc_id"])

    with client.test_client() as http:
        removed = http.delete(
            f"/api/workflow/{session_id}/slots/CURRENT_YEAR_SOURCES/documents/{fa['doc_id']}",
            headers={"X-User-Id": "user-a"})
    assert removed.status_code == 200

    assert _slots(_state(client, session_id))["CURRENT_YEAR_SOURCES"] == [appendix["doc_id"]]


# ---------------------------------------------------------------------------
# USER ISOLATION UNDER MULTI-DOCUMENT INTAKE
# ---------------------------------------------------------------------------

def test_two_users_intakes_do_not_mix(client):
    a1 = _upload(client, FIXTURE_DOCX, user="user-a")
    session_a = a1["session_id"]
    a2 = _upload(client, FIXTURE_DOCX, session_a, user="user-a")
    _start(client, session_a, user="user-a")
    _assign(client, session_a, "CURRENT_YEAR_SOURCES", a1["doc_id"], user="user-a")
    _assign(client, session_a, "HISTORICAL_LOCAL_FILE", a2["doc_id"], user="user-a")

    b1 = _upload(client, FIXTURE_DOCX, user="user-b")
    session_b = b1["session_id"]
    _start(client, session_b, user="user-b")
    _assign(client, session_b, "CURRENT_YEAR_SOURCES", b1["doc_id"], user="user-b")

    state_a = _state(client, session_a, user="user-a")
    state_b = _state(client, session_b, user="user-b")

    assert _total_assigned(state_a) == 2
    assert _total_assigned(state_b) == 1
    assert state_a["workflow_id"] != state_b["workflow_id"]

    a_docs = {d for ids in _slots(state_a).values() for d in ids}
    b_docs = {d for ids in _slots(state_b).values() for d in ids}
    assert a_docs.isdisjoint(b_docs)

    with client.test_client() as http:
        cross = http.get(f"/api/workflow/{session_a}", headers={"X-User-Id": "user-b"})
    assert cross.status_code in (403, 404)

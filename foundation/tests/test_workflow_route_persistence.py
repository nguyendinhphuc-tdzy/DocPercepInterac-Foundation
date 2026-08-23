"""
Workflow intake persistence through the API (Phase PROD-UX-1 hardening, P0-1).

The acceptance criteria this file encodes:

    upload -> assign slots -> refresh browser        => slots persist
    upload -> assign slots -> backend restarts       => slots persist
    user A's workflow                                => invisible to user B

"Restart" is simulated the way it actually happens on Render: every repository
object is discarded and rebuilt, so anything that only lived in the process is
gone. Whatever survives came from the repository.
"""
from __future__ import annotations

import io
import json
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

warnings.filterwarnings("ignore")

FIXTURE_DOCX = Path(__file__).resolve().parent / "fixtures" / "fixture_generic_handbook.docx"
DEMO_ROOT = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
HISTORICAL_DOCX = DEMO_ROOT / "Compare LF" / "HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx"

pytestmark = pytest.mark.skipif(
    not FIXTURE_DOCX.exists(), reason="generic docx fixture is not present")


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
    yield app.test_client()
    reset_repositories()


def _restart_backend():
    """Discard every repository instance, as a redeploy would."""
    from adapters.repository import reset_repositories

    reset_repositories()


def _upload(client, path: Path, session_id: str | None = None, user: str = "user-a"):
    data = {"file": (io.BytesIO(path.read_bytes()), path.name)}
    if session_id:
        data["session_id"] = session_id
    return client.post("/api/documents", data=data,
                       content_type="multipart/form-data",
                       headers={"X-User-Id": user})


def _start_workflow(client, session_id: str, user: str = "user-a"):
    return client.post("/api/workflow/sessions",
                       json={"session_id": session_id,
                             "workflow": "LOCAL_FILE_ROLL_FORWARD"},
                       headers={"X-User-Id": user})


def _assign(client, session_id: str, slot: str, doc_id: str, user: str = "user-a"):
    return client.post(f"/api/workflow/{session_id}/slots/{slot}/assign",
                       json={"doc_id": doc_id}, headers={"X-User-Id": user})


def _get_workflow(client, session_id: str, user: str = "user-a"):
    return client.get(f"/api/workflow/{session_id}", headers={"X-User-Id": user})


def _slot(payload: dict, slot_id: str) -> dict:
    return next(s for s in payload["slots"] if s["slot_id"] == slot_id)


@pytest.fixture
def workflow_with_a_source(client):
    """A started workflow holding one assigned current-year source."""
    upload = _upload(client, FIXTURE_DOCX)
    assert upload.status_code == 200
    summary = upload.get_json()
    session_id, doc_id = summary["session_id"], summary["doc_id"]

    assert _start_workflow(client, session_id).status_code == 200
    assigned = _assign(client, session_id, "CURRENT_YEAR_SOURCES", doc_id)
    assert assigned.status_code == 200, assigned.get_json()
    return session_id, doc_id


# ---------------------------------------------------------------------------
# REFRESH
# ---------------------------------------------------------------------------

def test_workflow_survives_a_browser_refresh(client, workflow_with_a_source):
    session_id, doc_id = workflow_with_a_source

    # A refresh is exactly this: the client asks the server for the state again.
    reloaded = _get_workflow(client, session_id)
    assert reloaded.status_code == 200

    slot = _slot(reloaded.get_json(), "CURRENT_YEAR_SOURCES")
    assert slot["assigned_document_ids"] == [doc_id]
    assert slot["assignments"][0]["filename"] == FIXTURE_DOCX.name


def test_slot_verdicts_and_readiness_are_rebuilt_on_reload(client, workflow_with_a_source):
    session_id, _ = workflow_with_a_source
    payload = _get_workflow(client, session_id).get_json()

    assert payload["gate"]["execution_allowed"] is False
    assert payload["gate"]["message"]
    assert len(payload["readiness"]) == 5
    assert _slot(payload, "CURRENT_YEAR_SOURCES")["assignments"][0]["validation_status"] \
        in ("ROLE_CONFIRMED", "HUMAN_REVIEW", "ROLE_MISMATCH")


# ---------------------------------------------------------------------------
# RESTART / REDEPLOY
# ---------------------------------------------------------------------------

def test_workflow_survives_a_backend_restart(client, workflow_with_a_source):
    session_id, doc_id = workflow_with_a_source

    _restart_backend()

    reloaded = _get_workflow(client, session_id)
    assert reloaded.status_code == 200
    assert _slot(reloaded.get_json(), "CURRENT_YEAR_SOURCES")["assigned_document_ids"] == [doc_id]


def test_restart_preserves_the_workflow_identity(client, workflow_with_a_source):
    session_id, _ = workflow_with_a_source
    before = _get_workflow(client, session_id).get_json()["workflow_id"]

    _restart_backend()

    after = _get_workflow(client, session_id).get_json()["workflow_id"]
    assert after == before


def test_restarting_does_not_start_a_second_workflow(client, workflow_with_a_source):
    session_id, doc_id = workflow_with_a_source
    workflow_id = _get_workflow(client, session_id).get_json()["workflow_id"]

    _restart_backend()

    # Re-entering the workflow re-attaches rather than creating a competing one.
    restarted = _start_workflow(client, session_id)
    assert restarted.status_code == 200
    payload = restarted.get_json()
    assert payload["workflow_id"] == workflow_id
    assert _slot(payload, "CURRENT_YEAR_SOURCES")["assigned_document_ids"] == [doc_id]


def test_agent_context_survives_a_restart(client, workflow_with_a_source):
    session_id, doc_id = workflow_with_a_source

    _restart_backend()

    context = client.get(f"/api/workflow/{session_id}/agent-context",
                         headers={"X-User-Id": "user-a"}).get_json()
    assert context["workflow"] == "LOCAL_FILE_ROLL_FORWARD"
    assert context["current_source_document_ids"] in ([doc_id], [])


# ---------------------------------------------------------------------------
# USER ISOLATION
# ---------------------------------------------------------------------------

def test_user_b_cannot_read_user_a_workflow(client, workflow_with_a_source):
    session_id, _ = workflow_with_a_source
    response = _get_workflow(client, session_id, user="user-b")
    assert response.status_code in (403, 404)
    assert "slots" not in (response.get_json() or {})


def test_user_b_cannot_assign_into_user_a_workflow(client, workflow_with_a_source):
    session_id, doc_id = workflow_with_a_source
    response = _assign(client, session_id, "MASTER_TEMPLATE", doc_id, user="user-b")
    assert response.status_code in (403, 404)


def test_user_b_starting_a_workflow_does_not_expose_user_a_documents(client,
                                                                     workflow_with_a_source):
    session_id, _ = workflow_with_a_source
    response = _start_workflow(client, session_id, user="user-b")
    if response.status_code == 200:
        # A separate intake for user B is acceptable; leaking user A's files is not.
        for slot in response.get_json()["slots"]:
            assert slot["assigned_document_ids"] == []
    else:
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# WHAT IS STORED
# ---------------------------------------------------------------------------

def test_no_document_bytes_are_written_into_workflow_state(client, workflow_with_a_source,
                                                           tmp_path):
    from adapters.repository import LocalWorkflowRepository

    session_id, doc_id = workflow_with_a_source
    state_file = tmp_path / session_id / LocalWorkflowRepository.FILENAME
    assert state_file.exists(), "workflow state was not persisted at all"

    state = json.loads(state_file.read_text(encoding="utf-8"))
    assignment = state["assignments"][0]

    assert assignment["document_id"] == doc_id       # a reference to the bytes
    assert assignment["file_hash"]                   # a fact about the bytes
    assert not any(key in assignment for key in ("content", "bytes", "blob", "data"))
    assert len(state_file.read_bytes()) < 64 * 1024  # metadata, not a document


def test_persisted_state_carries_the_required_columns(client, workflow_with_a_source,
                                                      tmp_path):
    from adapters.repository import LocalWorkflowRepository

    session_id, _ = workflow_with_a_source
    state = json.loads(
        (tmp_path / session_id / LocalWorkflowRepository.FILENAME).read_text(encoding="utf-8"))

    workflow = state["workflow"]
    for column in ("workflow_id", "user_id", "session_id", "workflow_type",
                   "created_at", "updated_at"):
        assert workflow.get(column) is not None, f"missing {column}"

    assignment = state["assignments"][0]
    for column in ("workflow_id", "user_id", "session_id", "slot_id", "document_id",
                   "validation_status", "readiness_status", "created_at", "updated_at"):
        assert assignment.get(column) is not None, f"missing {column}"


@pytest.mark.skipif(not HISTORICAL_DOCX.exists(), reason="demo fixtures are not present")
def test_a_real_role_verdict_is_rebuilt_after_restart(client):
    """The verdict is recomputed from the stored profile, not re-read from the file."""
    summary = _upload(client, HISTORICAL_DOCX).get_json()
    session_id, doc_id = summary["session_id"], summary["doc_id"]
    _start_workflow(client, session_id)
    assigned = _assign(client, session_id, "HISTORICAL_LOCAL_FILE", doc_id)
    assert assigned.status_code == 200

    before = _slot(assigned.get_json(), "HISTORICAL_LOCAL_FILE")["assignments"][0]
    assert before["validation_status"] == "ROLE_CONFIRMED"

    _restart_backend()

    after = _slot(_get_workflow(client, session_id).get_json(),
                  "HISTORICAL_LOCAL_FILE")["assignments"][0]
    assert after["validation_status"] == before["validation_status"]
    assert after["detected_label"] == before["detected_label"]
    assert after["signals"]["fiscal_year"] == before["signals"]["fiscal_year"]

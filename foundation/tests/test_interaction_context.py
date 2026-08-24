"""
Interaction context — the user's selection is evidence, not decoration (P0-A).

The defect: a user selected a cell, the chip showed it, the request carried an
id — and the backend dropped it. `ContextBuilder` only resolved a selected
element when an `active_doc_id` was set, and with several documents open and
none "active" it set `active_doc_id = None`, so the selection silently vanished
and the Agent answered from the prompt alone.

What is pinned here:

     1. the payload schema is validated
     2. a selected element must belong to the document it names
     3. that document must belong to the session
     4. an invalid selection is a 4xx, never a shrug
     5. a workflow id must belong to the session
     6. ContextBuilder carries the verified selection through
     7. workflow slots stay authoritative alongside a selection
     8. selected evidence outranks the generic workspace listing
     9. the selection reaches the model's prompt and the response's citations
    10. a selection is never silently dropped
"""
from __future__ import annotations

import io
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from applications.agent.context_builder import ContextBuilder  # noqa: E402
from applications.agent.interaction_context import (  # noqa: E402
    InteractionContextError,
    InteractionContextVerifier,
    VerifiedInteractionContext,
    VerifiedSelection,
)

warnings.filterwarnings("ignore")

FIXTURE_DOCX = Path(__file__).resolve().parent / "fixtures" / "fixture_generic_handbook.docx"
DEMO = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
FA_RPT = DEMO / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

pytestmark = pytest.mark.skipif(
    not FIXTURE_DOCX.exists(), reason="generic docx fixture is not present")


@pytest.fixture
def app(monkeypatch, tmp_path):
    import adapters.repository as repository_module
    import api.routes.documents as documents_module
    import api.routes.workflow as workflow_module
    import applications.agent.context_builder as context_builder_module
    import applications.agent.orchestrator as orchestrator_module
    from adapters.repository import reset_repositories
    from api.app import create_app

    monkeypatch.setattr(documents_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(workflow_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(repository_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(context_builder_module, "UPLOAD_ROOT", tmp_path)
    monkeypatch.setattr(orchestrator_module, "UPLOAD_ROOT", tmp_path)
    reset_repositories()

    application = create_app()
    application.config.update(TESTING=True)
    yield application
    reset_repositories()


def _upload(app, path: Path, session_id: str | None = None):
    data = {"file": (io.BytesIO(path.read_bytes()), path.name)}
    if session_id:
        data["session_id"] = session_id
    with app.test_client() as http:
        response = http.post("/api/documents", data=data,
                             content_type="multipart/form-data")
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _first_element(app, session_id: str, doc_id: str):
    with app.test_client() as http:
        elements = http.get(
            f"/api/documents/{session_id}/elements/{doc_id}").get_json()["elements"]
    return next(e for e in elements if e.get("text"))


def _selection_payload(session_id, doc_id, element, **overrides):
    payload = {
        "session_id": session_id,
        "active_document_id": doc_id,
        "selected_elements": [{
            "document_id": doc_id,
            "element_id": element["element_id"],
            "element_type": element["type"],
            "display_label": element.get("name", ""),
            "location": {},
            "selection_source": "document_view",
        }],
        "selected_regions": [],
        "selected_documents": [],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def selected(app):
    """A session with one document and a real element selected in it."""
    uploaded = _upload(app, FIXTURE_DOCX)
    element = _first_element(app, uploaded["session_id"], uploaded["doc_id"])
    return app, uploaded["session_id"], uploaded["doc_id"], element


# ---------------------------------------------------------------------------
# 1-5. VALIDATION
# ---------------------------------------------------------------------------

def test_schema_accepts_an_empty_context():
    verified = InteractionContextVerifier.verify({}, session_id=None)
    assert verified.selected_elements == []
    assert verified.has_selection is False


def test_a_selected_element_is_verified_against_its_document(selected):
    app, session_id, doc_id, element = selected
    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element), session_id=session_id)

    assert len(verified.selected_elements) == 1
    resolved = verified.selected_elements[0]
    assert resolved.element_id == element["element_id"]
    assert resolved.document_id == doc_id
    assert resolved.document_name == FIXTURE_DOCX.name


def test_metadata_is_rebuilt_not_trusted(selected):
    """A lying client cannot rename or relocate the element it selected."""
    app, session_id, doc_id, element = selected
    payload = _selection_payload(session_id, doc_id, element)
    payload["selected_elements"][0]["display_label"] = "TOTALLY WRONG LABEL"
    payload["selected_elements"][0]["element_type"] = "not_a_type"
    payload["selected_elements"][0]["location"] = {"sheet_name": "Fabricated"}

    resolved = InteractionContextVerifier.verify(
        payload, session_id=session_id).selected_elements[0]

    assert resolved.display_label != "TOTALLY WRONG LABEL"
    assert resolved.element_type != "not_a_type"
    assert resolved.location.get("sheet_name") != "Fabricated"


@pytest.mark.skipif(not FA_RPT.exists(), reason="demo workbook is not present")
def test_an_element_from_another_document_is_refused(selected):
    """element_id is content-derived, so it must be checked against the document
    it is claimed to live in — a different file simply does not contain it."""
    app, session_id, doc_id, element = selected
    other = _upload(app, FA_RPT, session_id)

    payload = _selection_payload(session_id, other["doc_id"], element)
    with pytest.raises(InteractionContextError) as exc:
        InteractionContextVerifier.verify(payload, session_id=session_id)
    assert exc.value.code == "unknown_element"


def test_a_document_from_another_session_is_refused(selected):
    app, session_id, doc_id, element = selected
    payload = _selection_payload(session_id, "doc-from-elsewhere", element)

    with pytest.raises(InteractionContextError) as exc:
        InteractionContextVerifier.verify(payload, session_id=session_id)
    assert exc.value.code == "unknown_document"


def test_an_unknown_element_id_is_refused(selected):
    app, session_id, doc_id, element = selected
    payload = _selection_payload(session_id, doc_id, {**element, "element_id": "made-up"})

    with pytest.raises(InteractionContextError) as exc:
        InteractionContextVerifier.verify(payload, session_id=session_id)
    assert exc.value.code == "unknown_element"


def test_a_workflow_id_that_is_not_this_sessions_is_refused(selected):
    app, session_id, doc_id, element = selected
    payload = _selection_payload(session_id, doc_id, element, workflow_id="wf-someone-else")

    with pytest.raises(InteractionContextError) as exc:
        InteractionContextVerifier.verify(payload, session_id=session_id)
    assert exc.value.code == "unknown_workflow"


def test_an_invalid_selection_returns_4xx_not_a_silent_drop(selected):
    app, session_id, doc_id, element = selected
    payload = _selection_payload(session_id, doc_id, {**element, "element_id": "ghost"})

    with app.test_client() as http:
        response = http.post("/api/agent/chat", json={
            "message": "Explain this value",
            "session_id": session_id,
            "interaction_context": payload,
        })

    assert response.status_code == 400
    body = response.get_json()
    assert body["error_type"] == "unknown_element"
    assert "ghost" in (body.get("element_id") or "")


# ---------------------------------------------------------------------------
# 6-8. CONTEXT PRIORITY
# ---------------------------------------------------------------------------

def test_context_builder_carries_the_selection(selected):
    app, session_id, doc_id, element = selected
    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element), session_id=session_id)

    context = ContextBuilder.build_context(session_id=session_id, interaction=verified)

    assert context.selected_evidence, "verified selection did not reach the context"
    assert context.selected_element["element_id"] == element["element_id"]
    assert context.interaction_context["selected_elements"][0]["element_id"] == element["element_id"]


def test_selection_resolves_without_an_active_document(selected):
    """The exact production drop: many documents, none active, selection lost."""
    app, session_id, doc_id, element = selected
    for _ in range(3):
        _upload(app, FIXTURE_DOCX, session_id)

    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element, active_document_id=None),
        session_id=session_id)
    context = ContextBuilder.build_context(
        session_id=session_id, active_doc_id=None, interaction=verified)

    assert len(context.available_documents) > 1        # ambiguous workspace
    assert context.selected_element is not None        # and still resolved
    assert context.active_doc_id == doc_id             # from the selection itself


def test_selected_evidence_outranks_the_generic_workspace(selected):
    app, session_id, doc_id, element = selected
    for _ in range(4):
        _upload(app, FIXTURE_DOCX, session_id)

    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element), session_id=session_id)
    context = ContextBuilder.build_context(session_id=session_id, interaction=verified)

    from applications.agent.orchestrator import AgentOrchestrator

    prompt = AgentOrchestrator._build_general_prompt(context)
    assert "SELECTED" in prompt
    assert element["element_id"] in prompt
    # The evidence block precedes the workspace listing.
    assert prompt.index("SELECTED") < prompt.index("Documents loaded")


def test_workflow_slots_stay_authoritative_next_to_a_selection(selected, monkeypatch):
    app, session_id, doc_id, element = selected

    workflow_context = {
        "workflow": "LOCAL_FILE_ROLL_FORWARD",
        "historical_document_id": "doc-hist",
        "current_source_document_ids": ["doc-fa"],
        "template_document_id": "doc-tpl",
        "inputs_complete": True, "execution_allowed": True, "readiness": [],
    }
    import applications.agent.context_builder as context_builder_module
    monkeypatch.setattr(context_builder_module, "_load_workflow_context",
                        lambda session_id, user_id="anonymous": workflow_context)

    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element), session_id=session_id)
    context = ContextBuilder.build_context(session_id=session_id, interaction=verified)

    assert context.workflow["historical_document_id"] == "doc-hist"
    assert context.selected_evidence[0]["element_id"] == element["element_id"]

    from applications.agent.orchestrator import AgentOrchestrator

    prompt = AgentOrchestrator._build_general_prompt(context)
    assert "LOCAL_FILE_ROLL_FORWARD" in prompt
    assert "do not re-derive them from filenames" in prompt
    assert element["element_id"] in prompt


# ---------------------------------------------------------------------------
# 9-10. THE SELECTION REACHES THE AGENT
# ---------------------------------------------------------------------------

def test_the_selection_reaches_the_model_and_the_citation(selected, monkeypatch):
    app, session_id, doc_id, element = selected
    seen = {}

    import applications.agent.orchestrator as orchestrator_module

    def _call(cls, message, system_prompt, *, spec):
        seen["prompt"] = system_prompt
        return "Explained."

    monkeypatch.setattr(orchestrator_module.AgentOrchestrator, "_call_model",
                        classmethod(_call))

    with app.test_client() as http:
        response = http.post("/api/agent/chat", json={
            "message": "Explain this value",
            "session_id": session_id,
            "context": {"selected_element_id": element["element_id"], "active_doc_id": doc_id},
            "interaction_context": _selection_payload(session_id, doc_id, element),
        })

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert seen.get("prompt"), "the model was never called"
    assert element["element_id"] in seen["prompt"], "the selection never reached the model"

    citations = body.get("citations") or []
    if citations:
        assert any(c["element_id"] == element["element_id"] for c in citations), citations


def test_a_selection_is_never_silently_dropped(selected, monkeypatch):
    """Either the selection is used, or the request fails. Never neither."""
    app, session_id, doc_id, element = selected
    prompts = []

    import applications.agent.orchestrator as orchestrator_module
    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "_call_model",
        classmethod(lambda cls, message, system_prompt, *, spec: prompts.append(system_prompt) or "ok"))

    with app.test_client() as http:
        response = http.post("/api/agent/chat", json={
            "message": "Summarise the workspace",
            "session_id": session_id,
            "interaction_context": _selection_payload(session_id, doc_id, element),
        })

    assert response.status_code == 200
    assert prompts and element["element_id"] in prompts[0]


def test_no_selection_means_no_evidence_block(selected, monkeypatch):
    """After Deselect the next request carries — and shows — nothing."""
    app, session_id, doc_id, _element = selected
    prompts = []

    import applications.agent.orchestrator as orchestrator_module
    monkeypatch.setattr(
        orchestrator_module.AgentOrchestrator, "_call_model",
        classmethod(lambda cls, message, system_prompt, *, spec: prompts.append(system_prompt) or "ok"))

    with app.test_client() as http:
        response = http.post("/api/agent/chat", json={
            "message": "Summarise the workspace",
            "session_id": session_id,
            "interaction_context": {"session_id": session_id, "active_document_id": doc_id,
                                    "selected_elements": [], "selected_regions": [],
                                    "selected_documents": []},
        })

    assert response.status_code == 200
    assert prompts and "SELECTED" not in prompts[0]


# ---------------------------------------------------------------------------
# TELEMETRY
# ---------------------------------------------------------------------------

def test_telemetry_counts_but_never_quotes(selected):
    app, session_id, doc_id, element = selected
    verified = InteractionContextVerifier.verify(
        _selection_payload(session_id, doc_id, element), session_id=session_id)

    telemetry = verified.telemetry()
    assert telemetry["selected_element_count"] == 1
    assert telemetry["selected_document_count"] == 1

    serialised = str(telemetry)
    assert element["text"][:20] not in serialised, "telemetry quoted document content"
    assert FIXTURE_DOCX.name not in serialised


def test_multi_selection_is_representable(selected):
    app, session_id, doc_id, element = selected
    with app.test_client() as http:
        elements = http.get(
            f"/api/documents/{session_id}/elements/{doc_id}").get_json()["elements"]
    second = next(e for e in elements
                  if e["element_id"] != element["element_id"] and e.get("text"))

    payload = _selection_payload(session_id, doc_id, element)
    payload["selected_elements"].append({
        "document_id": doc_id, "element_id": second["element_id"],
        "element_type": second["type"], "display_label": "", "location": {},
        "selection_source": "elements_pane",
    })

    verified = InteractionContextVerifier.verify(payload, session_id=session_id)
    assert len(verified.selected_elements) == 2
    assert verified.telemetry()["selected_element_count"] == 2

"""Comprehensive unit test suite for Foundation Agent Architecture & Governed Actions.

Tests Slices 1-6:
- Selected element summarization and citation generation (Slice 1)
- Search and provenance citations (Slice 2)
- Cross-document comparison (Slice 3)
- Edit proposal creation and capability gating (Slice 4)
- Server-side action execution by action_id (Slice 5)
- Freshness validation and writeback persistence (Slice 6)
"""
import io
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.agent.models import Citation, ProposedAction  # noqa: E402
from applications.agent.context_builder import ContextBuilder  # noqa: E402
from applications.agent.proposal_store import ProposalStore  # noqa: E402
from applications.agent.action_executor import ActionExecutor  # noqa: E402
from applications.workbench_client import WorkbenchResponse  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def mock_workbench():
    """Default autouse mock for Workbench to test Agent orchestrator logic without requiring live network."""
    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.return_value = WorkbenchResponse(
            content="Mocked response from KPMG Workbench.",
            model="gpt-5-6-luna-2026-07-09-gs-ae",
            usage={"prompt_tokens": 12, "completion_tokens": 10},
        )
        yield mock_cc


@pytest.fixture
def sample_session(client, tmp_path):
    """Creates a real session with uploaded DOCX & XLSX fixtures for testing."""
    root = Path(__file__).resolve().parents[2]
    docx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
    xlsx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

    # Upload DOCX
    with open(docx_fixture, "rb") as f:
        res = client.post(
            "/api/documents",
            data={"file": (f, "template.docx")},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    data = res.get_json()
    session_id = data["session_id"]
    docx_doc_id = data["doc_id"]

    # Upload XLSX into same session
    with open(xlsx_fixture, "rb") as f:
        res = client.post(
            "/api/documents",
            data={"file": (f, "financials.xlsx"), "session_id": session_id},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    xlsx_doc_id = res.get_json()["doc_id"]

    return {
        "session_id": session_id,
        "docx_doc_id": docx_doc_id,
        "xlsx_doc_id": xlsx_doc_id,
    }


def test_agent_chat_missing_message(client):
    res = client.post("/api/agent/chat", json={})
    assert res.status_code == 400
    assert "Message is required" in res.get_json()["error"]


def test_slice_1_selected_element_summarize_and_citation(client, sample_session):
    """Slice 1: Selected element -> Summarize -> Citation -> Reveal."""
    session_id = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    # Get elements of DOCX
    res_els = client.get(f"/api/documents/{session_id}/elements/{docx_doc_id}")
    assert res_els.status_code == 200
    elements = res_els.get_json()["elements"]
    target_el = elements[0]

    # Ask agent to explain/summarize the selected element
    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Explain this selected section.",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": target_el["element_id"],
            },
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "summarize_element"
    assert len(data["citations"]) > 0

    citation = data["citations"][0]
    assert citation["doc_id"] == docx_doc_id
    assert citation["element_id"] == target_el["element_id"]
    assert citation["doc_name"] == "template.docx"
    assert len(data["steps"]) > 0


def test_slice_2_deterministic_search_and_provenance(client, sample_session):
    """Slice 2: Search -> Answer -> Provenance citations."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Find tax in this document",
            "context": {
                "active_doc_id": xlsx_doc_id,
            },
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "search_elements"
    assert len(data["citations"]) > 0
    assert all(c["doc_id"] == xlsx_doc_id for c in data["citations"])


def test_slice_3_cross_document_compare(client, sample_session):
    """Slice 3: Cross-document comparison across 2 documents in session."""
    session_id = sample_session["session_id"]

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Compare the structure of these documents",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "compare_documents"
    assert len(data["citations"]) >= 2
    doc_ids_cited = {c["doc_id"] for c in data["citations"]}
    assert sample_session["docx_doc_id"] in doc_ids_cited
    assert sample_session["xlsx_doc_id"] in doc_ids_cited


def test_slice_4_edit_proposal_governance(client, sample_session):
    """Slice 4: Propose edit creates structured ProposedAction requiring user confirmation."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    # Get editable cell in XLSX
    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    elements = res_els.get_json()["elements"]
    editable_cell = next(e for e in elements if e["capabilities"]["editable"] and e["text"])

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": f"Change this cell to 'ACME Corp Ltd'",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["intent"] == "propose_edit"
    assert len(data["proposed_actions"]) == 1

    proposal = data["proposed_actions"][0]
    assert proposal["element_id"] == editable_cell["element_id"]
    assert proposal["doc_id"] == xlsx_doc_id
    assert proposal["current_value"] == editable_cell["text"]
    assert proposal["proposed_value"] == "ACME Corp Ltd"
    assert proposal["requires_confirmation"] is True
    assert proposal["status"] == "proposed"

    # Verify proposal is persisted server-side
    stored = ProposalStore.get_proposal(session_id, proposal["action_id"])
    assert stored is not None
    assert stored.element_id == editable_cell["element_id"]


def test_slice_5_and_6_governed_action_execution_and_writeback(client, sample_session):
    """Slice 5 & 6: Confirmed execution via action_id persists edit to disk via WritebackEngine."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    elements = res_els.get_json()["elements"]
    editable_cell = next(e for e in elements if e["capabilities"]["editable"] and e["text"])

    # 1. Propose edit
    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Update this cell to 'GOVERNED_EXECUTION_2026'",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    # 2. Execute proposal strictly by action_id
    res_exec = client.post(
        "/api/agent/action/execute",
        json={
            "session_id": session_id,
            "action_id": action_id,
        },
    )
    assert res_exec.status_code == 200
    exec_data = res_exec.get_json()
    assert exec_data["status"] == "success"
    assert exec_data["new_value"] == "GOVERNED_EXECUTION_2026"
    assert exec_data["element_id"] == editable_cell["element_id"]

    # 3. Verify server-side state has updated
    res_els_after = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    updated_el = next(
        e for e in res_els_after.get_json()["elements"]
        if e["anchor"]["cell_address"] == editable_cell["anchor"]["cell_address"]
        and e["anchor"]["sheet_name"] == editable_cell["anchor"]["sheet_name"]
    )
    assert updated_el["text"] == "GOVERNED_EXECUTION_2026"

    # 4. Attempting to execute the same proposal again must fail
    res_dup = client.post(
        "/api/agent/action/execute",
        json={
            "session_id": session_id,
            "action_id": action_id,
        },
    )
    assert res_dup.status_code == 400
    assert "already been applied" in res_dup.get_json()["error"]


# ============================================================================
# LUNA / SOL MODEL SELECTION TESTS
# ============================================================================

def test_agent_get_models_endpoint(client):
    """GET /api/agent/models returns exact allowlist with Luna as default."""
    res = client.get("/api/agent/models")
    assert res.status_code == 200
    data = res.get_json()
    assert data["default"] == "luna"
    models = data["models"]
    assert len(models) == 2
    model_ids = {m["id"] for m in models}
    assert model_ids == {"luna", "sol"}
    luna_meta = next(m for m in models if m["id"] == "luna")
    assert luna_meta["is_default"] is True
    assert "Everyday" in luna_meta["description"]
    sol_meta = next(m for m in models if m["id"] == "sol")
    assert sol_meta["is_default"] is False
    assert "Deep reasoning" in sol_meta["description"]


def test_agent_chat_default_model_is_luna(client, sample_session):
    """Missing model parameter defaults safely to Luna without error."""
    session_id = sample_session["session_id"]
    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Summarize the workspace documents.",
        },
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["model"] == "luna"
    assert data["status"] == "success"


def test_agent_chat_explicit_luna(client, sample_session):
    """Explicit model='luna' is resolved and returned in response."""
    session_id = sample_session["session_id"]
    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.return_value = WorkbenchResponse(
            content="Luna summary response",
            model="gpt-5-6-luna-2026-07-09-gs-ae",
        )
        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this quickly.",
                "model": "luna",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["model"] == "luna"
        assert data["response"] == "Luna summary response"
        mock_cc.assert_called_once()
        assert mock_cc.call_args.kwargs.get("model") == "gpt-5-6-luna-2026-07-09-gs-ae"


def test_agent_chat_explicit_sol(client, sample_session):
    """Explicit model='sol' is mapped to gpt-5-6-sol-2026-07-09-gs-ae and returned."""
    session_id = sample_session["session_id"]
    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.return_value = WorkbenchResponse(
            content="Sol deep reasoning response",
            model="gpt-5-6-sol-2026-07-09-gs-ae",
        )
        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Analyze complex structures in depth.",
                "model": "sol",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["model"] == "sol"
        assert data["response"] == "Sol deep reasoning response"
        mock_cc.assert_called_once()
        assert mock_cc.call_args.kwargs.get("model") == "gpt-5-6-sol-2026-07-09-gs-ae"


def test_agent_chat_unknown_model_rejected(client, sample_session):
    """Unknown, third-party, or invalid model strings are rejected with 400 Bad Request."""
    session_id = sample_session["session_id"]
    for bad_model in ["gpt-4o", "gpt-5-4-mini", "terra", "o3", "unknown_model"]:
        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Hello",
                "model": bad_model,
            },
        )
        assert res.status_code == 400
        assert "Unsupported model" in res.get_json()["error"]


def test_agent_chat_empty_model_rejected(client, sample_session):
    """Empty or whitespace model strings are rejected with 400."""
    session_id = sample_session["session_id"]
    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Hello",
            "model": "   ",
        },
    )
    assert res.status_code == 400
    assert "Invalid model" in res.get_json()["error"]


def test_agent_model_context_invariance(client, sample_session):
    """Context invariance: Selecting the same element with Luna vs Sol yields identical context semantics."""
    session_id = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{docx_doc_id}")
    elements = res_els.get_json()["elements"]
    target_el = elements[0]

    # Ask with Luna
    res_luna = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Explain this selected element.",
            "model": "luna",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": target_el["element_id"],
            },
        },
    )
    assert res_luna.status_code == 200
    data_luna = res_luna.get_json()
    assert data_luna["model"] == "luna"
    assert data_luna["intent"] == "summarize_element"
    assert len(data_luna["citations"]) == 1
    assert data_luna["citations"][0]["element_id"] == target_el["element_id"]

    # Switch to Sol with identical context
    res_sol = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Explain this selected element in detail.",
            "model": "sol",
            "context": {
                "active_doc_id": docx_doc_id,
                "selected_element_id": target_el["element_id"],
            },
        },
    )
    assert res_sol.status_code == 200
    data_sol = res_sol.get_json()
    assert data_sol["model"] == "sol"
    assert data_sol["intent"] == "summarize_element"
    assert len(data_sol["citations"]) == 1
    assert data_sol["citations"][0]["element_id"] == target_el["element_id"]
    assert data_sol["citations"][0]["doc_id"] == data_luna["citations"][0]["doc_id"]


def test_agent_model_write_governance_invariance(client, sample_session):
    """Write governance invariance: Luna and Sol undergo identical capability gating and action_id lifecycle."""
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    elements = res_els.get_json()["elements"]
    editable_cell = next(e for e in elements if e["capabilities"]["editable"] and e["text"])

    # 1. Propose with Luna
    res_luna = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Update cell to 'LUNA_PROPOSAL_VAL'",
            "model": "luna",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    assert res_luna.status_code == 200
    luna_actions = res_luna.get_json()["proposed_actions"]
    assert len(luna_actions) == 1
    assert luna_actions[0]["requires_confirmation"] is True
    assert luna_actions[0]["proposed_value"] == "LUNA_PROPOSAL_VAL"

    # 2. Propose with Sol
    res_sol = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Update cell to 'SOL_PROPOSAL_VAL'",
            "model": "sol",
            "context": {
                "active_doc_id": xlsx_doc_id,
                "selected_element_id": editable_cell["element_id"],
            },
        },
    )
    assert res_sol.status_code == 200
    sol_actions = res_sol.get_json()["proposed_actions"]
    assert len(sol_actions) == 1
    assert sol_actions[0]["requires_confirmation"] is True
    assert sol_actions[0]["proposed_value"] == "SOL_PROPOSAL_VAL"

    # 3. Sol proposal cannot bypass confirmation
    sol_action_id = sol_actions[0]["action_id"]
    res_exec = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": sol_action_id},
    )
    assert res_exec.status_code == 200
    assert res_exec.get_json()["new_value"] == "SOL_PROPOSAL_VAL"


def test_agent_model_provider_error_no_silent_fallback(client, sample_session):
    """Provider unavailable raises explicit error without silent fallback to the other model."""
    session_id = sample_session["session_id"]
    from applications.workbench_client import WorkbenchUnavailableError

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Deployment 'gpt-5-6-sol-2026-07-09-gs-ae' is temporarily overloaded.")
        
        # When Workbench fails, explicit 503 error is returned without changing model and without local fallback text
        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Give me deep analysis",
                "model": "sol",
            },
        )
        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "unavailable"
        assert data["model"] == "sol"  # Must NOT silently switch to luna
        assert "Sol is currently unavailable" in data["error"]
        assert "response" not in data or data.get("response") is None

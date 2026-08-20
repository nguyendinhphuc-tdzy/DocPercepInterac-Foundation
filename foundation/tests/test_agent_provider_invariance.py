"""Context, tool and governance invariance across all four selectable models.

The model and provider change; Foundation does not. Every assertion here runs
the *same* Foundation state through each of the four model ids and requires
byte-identical identity semantics out the other side: same session, same
document ids, same element ids, same citations, same capability checks, same
proposal lifecycle, same confirmation requirement.

If any of these ever diverge by provider, something has grown a
provider-specific context builder or a provider-specific tool permission — both
of which this phase forbids.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.agent.models import AGENT_MODEL_ORDER, AGENT_MODELS  # noqa: E402
from applications.agent.proposal_store import ProposalStore  # noqa: E402
from applications.workbench_client import WorkbenchResponse  # noqa: E402
from tests.gemini_mocks import gemini_ok_response  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DOCX = ROOT / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
FIXTURE_XLSX = ROOT / "anonymize client" / "Demo files" / "Demo files" / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

ALL_MODEL_IDS = list(AGENT_MODEL_ORDER)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def session_with_docs(client):
    with open(FIXTURE_DOCX, "rb") as f:
        res = client.post(
            "/api/documents",
            data={"file": (f, "invariance_template.docx")},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    session_id = res.get_json()["session_id"]
    docx_doc_id = res.get_json()["doc_id"]

    with open(FIXTURE_XLSX, "rb") as f:
        res2 = client.post(
            "/api/documents",
            data={"file": (f, "invariance_financials.xlsx"), "session_id": session_id},
            content_type="multipart/form-data",
        )
    assert res2.status_code == 200
    xlsx_doc_id = res2.get_json()["doc_id"]

    return {
        "session_id": session_id,
        "docx_doc_id": docx_doc_id,
        "xlsx_doc_id": xlsx_doc_id,
    }


@pytest.fixture
def all_providers_ok(gemini_enabled):
    """Mock both providers to succeed, so only Foundation semantics vary."""
    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
         patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
        mock_wb.return_value = WorkbenchResponse(
            content="Model answer.", model="mocked-workbench-deployment"
        )
        mock_gemini.return_value = gemini_ok_response("Model answer.")
        yield {"workbench": mock_wb, "gemini": mock_gemini}


def _ask(client, session_id, message, model_id, context=None):
    return client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": message,
            "model_id": model_id,
            "context": context or {},
        },
    )


# ============================================================================
# CONTEXT INVARIANCE
# ============================================================================

def test_selected_element_citation_identical_across_all_four_models(
    client, session_with_docs, all_providers_ok
):
    session_id = session_with_docs["session_id"]
    docx_doc_id = session_with_docs["docx_doc_id"]

    elements = client.get(
        f"/api/documents/{session_id}/elements/{docx_doc_id}"
    ).get_json()["elements"]
    target = elements[0]
    context = {
        "active_doc_id": docx_doc_id,
        "selected_element_id": target["element_id"],
    }

    signatures = {}
    for model_id in ALL_MODEL_IDS:
        res = _ask(client, session_id, "Explain this selected element.", model_id, context)
        assert res.status_code == 200, f"{model_id}: {res.get_json()}"
        data = res.get_json()

        assert data["model_id"] == model_id
        assert data["provider"] == AGENT_MODELS[model_id].provider

        # Foundation identity — must not vary by model.
        signatures[model_id] = {
            "intent": data["intent"],
            "citations": [
                {
                    "doc_id": c["doc_id"],
                    "element_id": c["element_id"],
                    "type": c["type"],
                    "element_name": c["element_name"],
                }
                for c in data["citations"]
            ],
        }

    reference = signatures[ALL_MODEL_IDS[0]]
    for model_id in ALL_MODEL_IDS[1:]:
        assert signatures[model_id] == reference, f"{model_id} diverged from reference"

    assert reference["intent"] == "summarize_element"
    assert len(reference["citations"]) == 1
    assert reference["citations"][0]["element_id"] == target["element_id"]
    assert reference["citations"][0]["doc_id"] == docx_doc_id


def test_search_citations_identical_across_all_four_models(
    client, session_with_docs, all_providers_ok
):
    session_id = session_with_docs["session_id"]
    docx_doc_id = session_with_docs["docx_doc_id"]
    context = {"active_doc_id": docx_doc_id}

    results = {}
    for model_id in ALL_MODEL_IDS:
        res = _ask(client, session_id, "Find revenue in this document", model_id, context)
        assert res.status_code == 200
        data = res.get_json()
        results[model_id] = (
            data["intent"],
            [(c["doc_id"], c["element_id"]) for c in data["citations"]],
        )

    reference = results[ALL_MODEL_IDS[0]]
    for model_id in ALL_MODEL_IDS[1:]:
        assert results[model_id] == reference, f"{model_id} resolved different targets"


def test_clarification_behaviour_identical_across_all_four_models(
    client, session_with_docs, all_providers_ok
):
    """Ambiguous document context clarifies the same way for every model."""
    session_id = session_with_docs["session_id"]

    for model_id in ALL_MODEL_IDS:
        res = _ask(client, session_id, "Find revenue", model_id, {})
        assert res.status_code == 200
        data = res.get_json()
        assert data["intent"] == "clarify_document", model_id
        assert data["citations"] == []
        assert data["proposed_actions"] == []


# ============================================================================
# TOOL / GOVERNANCE INVARIANCE
# ============================================================================

def test_edit_proposal_governance_identical_across_all_four_models(
    client, session_with_docs, all_providers_ok
):
    """Every model produces a proposal that still requires explicit confirmation,
    carries an action_id, and is persisted server-side in 'proposed' state."""
    session_id = session_with_docs["session_id"]
    xlsx_doc_id = session_with_docs["xlsx_doc_id"]

    elements = client.get(
        f"/api/documents/{session_id}/elements/{xlsx_doc_id}"
    ).get_json()["elements"]
    editable = next(
        (e for e in elements if e.get("capabilities", {}).get("editable")), None
    )
    assert editable is not None, "fixture must contain at least one editable element"

    context = {
        "active_doc_id": xlsx_doc_id,
        "selected_element_id": editable["element_id"],
    }

    for model_id in ALL_MODEL_IDS:
        res = _ask(
            client,
            session_id,
            'Change this cell to "INVARIANCE_CHECK"',
            model_id,
            context,
        )
        assert res.status_code == 200, model_id
        data = res.get_json()

        assert data["intent"] == "propose_edit", model_id
        actions = data["proposed_actions"]
        assert len(actions) == 1, model_id

        action = actions[0]
        assert action["requires_confirmation"] is True, model_id
        assert action["status"] == "proposed", model_id
        assert action["doc_id"] == xlsx_doc_id
        assert action["element_id"] == editable["element_id"]
        assert action["proposed_value"] == "INVARIANCE_CHECK"

        # The proposal really exists server-side under the same lifecycle.
        stored = ProposalStore.get_proposal(session_id, action["action_id"])
        assert stored is not None, model_id
        assert stored.status == "proposed", model_id
        assert stored.value_fingerprint, model_id


def test_read_only_capability_check_identical_across_all_four_models(
    client, session_with_docs, all_providers_ok
):
    """A read-only element is refused identically whichever model is selected —
    no provider gets a weaker capability check."""
    session_id = session_with_docs["session_id"]
    docx_doc_id = session_with_docs["docx_doc_id"]

    elements = client.get(
        f"/api/documents/{session_id}/elements/{docx_doc_id}"
    ).get_json()["elements"]
    read_only = next(
        (e for e in elements if not e.get("capabilities", {}).get("editable")), None
    )
    if read_only is None:
        pytest.skip("fixture contains no read-only element")

    context = {
        "active_doc_id": docx_doc_id,
        "selected_element_id": read_only["element_id"],
    }

    for model_id in ALL_MODEL_IDS:
        res = _ask(client, session_id, 'Change this to "X"', model_id, context)
        assert res.status_code == 200, model_id
        data = res.get_json()
        assert data["proposed_actions"] == [], model_id
        assert "read-only" in data["response"].lower(), model_id


def test_confirmation_is_required_regardless_of_proposing_model(
    client, session_with_docs, all_providers_ok
):
    """A Gemini-proposed edit goes through exactly the same confirm/execute
    endpoint and the same action_id gate as a Workbench-proposed one."""
    session_id = session_with_docs["session_id"]
    xlsx_doc_id = session_with_docs["xlsx_doc_id"]

    elements = client.get(
        f"/api/documents/{session_id}/elements/{xlsx_doc_id}"
    ).get_json()["elements"]
    editable = next(e for e in elements if e.get("capabilities", {}).get("editable"))
    context = {
        "active_doc_id": xlsx_doc_id,
        "selected_element_id": editable["element_id"],
    }

    res = _ask(
        client, session_id, 'Change this cell to "GEMINI_GOVERNED"', "gemini_3_6_flash", context
    )
    action = res.get_json()["proposed_actions"][0]

    # Nothing was written by proposing.
    assert ProposalStore.get_proposal(session_id, action["action_id"]).status == "proposed"

    # Execution requires the explicit confirm endpoint with the action_id.
    exec_res = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": action["action_id"]},
    )
    assert exec_res.status_code == 200
    assert exec_res.get_json()["new_value"] == "GEMINI_GOVERNED"

    # Replay is rejected by the same lifecycle guard.
    replay = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": action["action_id"]},
    )
    assert replay.status_code == 400


# ============================================================================
# PER-REQUEST PROVIDER SELECTION (no leaked global state)
# ============================================================================

def test_switching_models_across_requests_leaks_no_provider_state(
    client, session_with_docs, all_providers_ok
):
    """Interleaved requests each reach their own provider with their own model
    name. A Sol request must not leave Workbench state behind for a following
    Gemini request, and vice versa."""
    session_id = session_with_docs["session_id"]
    mock_wb = all_providers_ok["workbench"]
    mock_gemini = all_providers_ok["gemini"]

    sequence = [
        "workbench_luna",
        "gemini_3_6_flash",
        "workbench_sol",
        "gemini_3_5_flash",
        "workbench_luna",
    ]
    for model_id in sequence:
        res = _ask(client, session_id, "Summarize the workspace.", model_id)
        assert res.status_code == 200
        data = res.get_json()
        assert data["model_id"] == model_id
        assert data["provider"] == AGENT_MODELS[model_id].provider

    workbench_models = [c.kwargs["model"] for c in mock_wb.call_args_list]
    assert workbench_models == [
        "gpt-5-6-luna-2026-07-09-gs-ae",
        "gpt-5-6-sol-2026-07-09-gs-ae",
        "gpt-5-6-luna-2026-07-09-gs-ae",
    ]

    gemini_urls = [c.args[0] for c in mock_gemini.call_args_list]
    assert [u.rsplit("/", 1)[-1] for u in gemini_urls] == [
        "gemini-3.6-flash:generateContent",
        "gemini-3.5-flash:generateContent",
    ]


def test_response_never_exposes_raw_provider_model_names(
    client, session_with_docs, all_providers_ok
):
    session_id = session_with_docs["session_id"]
    for model_id in ALL_MODEL_IDS:
        res = _ask(client, session_id, "Summarize the workspace.", model_id)
        body = json.dumps(res.get_json())
        assert "gpt-5-6-luna-2026-07-09-gs-ae" not in body
        assert "gpt-5-6-sol-2026-07-09-gs-ae" not in body
        assert "gemini-3.6-flash" not in body
        assert "gemini-3.5-flash" not in body
        assert "generativelanguage.googleapis.com" not in body
        assert "api.workbench.kpmg" not in body

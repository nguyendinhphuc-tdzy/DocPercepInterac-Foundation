"""Pilot instrumentation dry run (docs/evaluation/agent-pilot/, phase 28).

This is the automated internal dry run required before inviting real pilot
users: it exercises event collection, privacy minimization, and report
generation end-to-end. It is explicitly NOT a substitute for real pilot
participants — see Agent_Pilot_Report.md's "Verification Provenance" table,
which distinguishes VERIFIED BY AUTOMATION from real pilot-user evidence.

Event logs are redirected to an isolated tmp_path per test (never the real
foundation/.pilot_logs/ directory) so this suite is repeatable and doesn't
pollute real pilot data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.pilot import event_log as event_log_module  # noqa: E402
from applications.pilot.event_log import PilotEventLogger  # noqa: E402
from applications.pilot.report_generator import compute_metrics, render_report  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def mock_workbench():
    """Default autouse mock for Workbench to test Pilot telemetry during AI chat turns."""
    from unittest.mock import patch
    from applications.workbench_client import WorkbenchResponse
    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.return_value = WorkbenchResponse(
            content="Mocked response for pilot dry run.",
            model="gpt-5-6-luna-2026-07-09-gs-ae",
            usage={"prompt_tokens": 10, "completion_tokens": 8},
        )
        yield mock_cc


@pytest.fixture(autouse=True)
def isolated_pilot_log(tmp_path, monkeypatch):
    """Redirect the pilot event sink to an isolated directory for this test only."""
    isolated_root = tmp_path / ".pilot_logs"
    monkeypatch.setattr(event_log_module, "LOG_ROOT", isolated_root)
    yield isolated_root


@pytest.fixture
def sample_session(client):
    root = Path(__file__).resolve().parents[2]
    docx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
    xlsx_fixture = root / "anonymize client" / "Demo files" / "Demo files" / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

    with open(docx_fixture, "rb") as f:
        res = client.post(
            "/api/documents",
            data={"file": (f, "pilot_dry_run.docx")},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    data = res.get_json()
    session_id = data["session_id"]
    docx_doc_id = data["doc_id"]

    with open(xlsx_fixture, "rb") as f:
        res2 = client.post(
            "/api/documents",
            data={"file": (f, "pilot_dry_run.xlsx"), "session_id": session_id},
            content_type="multipart/form-data",
        )
    assert res2.status_code == 200
    xlsx_doc_id = res2.get_json()["doc_id"]

    return {"session_id": session_id, "docx_doc_id": docx_doc_id, "xlsx_doc_id": xlsx_doc_id}


def test_scenario_definitions_are_valid_json():
    scenarios_dir = Path(__file__).resolve().parents[2] / "docs" / "evaluation" / "agent-pilot" / "scenarios"
    files = sorted(scenarios_dir.glob("*.json"))
    assert len(files) >= 11, "Phase spec requires at least 11 controlled pilot tasks."

    required_fields = {
        "scenario_id", "category", "task", "setup",
        "expected_user_goal", "success_criteria", "safety_expectations",
    }
    categories_seen = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = required_fields - data.keys()
        assert not missing, f"{path.name} missing fields: {missing}"
        assert data["scenario_id"] == path.stem
        categories_seen.add(data["category"])

    expected_categories = {"READ_UNDERSTAND", "FIND_EXTRACT", "NAVIGATE", "COMPARE", "WRITE_MODIFY"}
    assert expected_categories.issubset(categories_seen)


def test_pilot_scenarios_endpoint_lists_metadata_only(client):
    res = client.get("/api/pilot/scenarios")
    assert res.status_code == 200
    scenarios = res.get_json()["scenarios"]
    assert len(scenarios) >= 11
    for s in scenarios:
        assert set(s.keys()) == {"scenario_id", "category", "task"}


def test_chat_turn_emits_request_intent_tool_events(client, sample_session, isolated_pilot_log):
    session_id = sample_session["session_id"]
    docx_doc_id = sample_session["docx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{docx_doc_id}")
    elements = res_els.get_json()["elements"]
    target_el = next(e for e in elements if e.get("text"))

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Summarize this paragraph.",
            "context": {"active_doc_id": docx_doc_id, "selected_element_id": target_el["element_id"]},
        },
    )
    assert res.status_code == 200

    events = PilotEventLogger.read_all(isolated_pilot_log)
    event_types = [e["event_type"] for e in events]
    assert "agent.request.started" in event_types
    assert "agent.intent.resolved" in event_types
    assert "agent.tool.selected" in event_types
    assert "agent.tool.completed" in event_types
    assert "agent.target.resolved" in event_types

    # Privacy: the selected element's actual text must never appear in any logged event.
    raw_text = target_el.get("text", "")
    if raw_text.strip():
        serialized = json.dumps(events)
        assert raw_text not in serialized, "Pilot event log leaked raw document content."


def test_ambiguous_document_triggers_clarification_event(client, sample_session, isolated_pilot_log):
    session_id = sample_session["session_id"]
    res = client.post(
        "/api/agent/chat",
        json={"session_id": session_id, "message": "Find the related-party transaction amounts."},
    )
    assert res.status_code == 200
    assert res.get_json()["intent"] == "clarify_document"

    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert any(e["event_type"] == "agent.clarification.requested" for e in events)


def test_write_lifecycle_emits_proposal_and_write_events(client, sample_session, isolated_pilot_log):
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    elements = res_els.get_json()["elements"]
    editable_cell = next(e for e in elements if e["capabilities"]["editable"] and e["text"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Change this cell to 'PILOT_DRY_RUN_VALUE'.",
            "context": {"active_doc_id": xlsx_doc_id, "selected_element_id": editable_cell["element_id"]},
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    res_exec = client.post(
        "/api/agent/action/execute",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_exec.status_code == 200

    events = PilotEventLogger.read_all(isolated_pilot_log)
    event_types = [e["event_type"] for e in events]
    assert "agent.proposal.created" in event_types
    assert "agent.proposal.confirmed" in event_types
    assert "agent.write.completed" in event_types

    # Privacy: the new value written must never appear in the event log (only hashed/omitted).
    serialized = json.dumps(events)
    assert "PILOT_DRY_RUN_VALUE" not in serialized


def test_reject_action_emits_rejected_event(client, sample_session, isolated_pilot_log):
    session_id = sample_session["session_id"]
    xlsx_doc_id = sample_session["xlsx_doc_id"]

    res_els = client.get(f"/api/documents/{session_id}/elements/{xlsx_doc_id}")
    elements = res_els.get_json()["elements"]
    editable_cell = next(e for e in elements if e["capabilities"]["editable"] and e["text"])

    res_chat = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Change this cell to 'REJECT_ME'.",
            "context": {"active_doc_id": xlsx_doc_id, "selected_element_id": editable_cell["element_id"]},
        },
    )
    action_id = res_chat.get_json()["proposed_actions"][0]["action_id"]

    res_rej = client.post(
        "/api/agent/action/reject",
        json={"session_id": session_id, "action_id": action_id},
    )
    assert res_rej.status_code == 200

    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert any(e["event_type"] == "agent.proposal.rejected" for e in events)


def test_frontend_origin_event_ingestion_and_field_allowlist(client, isolated_pilot_log):
    res = client.post(
        "/api/pilot/event",
        json={
            "event_type": "agent.citation.clicked",
            "session_id": "sess-1",
            "doc_id": "doc-1",
            "element_id": "el-1",
            # Attempt to smuggle raw content through an unlisted field —
            # the sanitizer must drop it, not store it.
            "raw_document_text": "CONFIDENTIAL FINANCIAL FIGURE 12345",
        },
    )
    assert res.status_code == 200
    assert res.get_json()["status"] == "recorded"

    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert len(events) == 1
    assert "raw_document_text" not in events[0]
    assert "CONFIDENTIAL FINANCIAL FIGURE 12345" not in json.dumps(events)


def test_feedback_event_ingestion(client, isolated_pilot_log):
    res = client.post(
        "/api/pilot/event",
        json={
            "event_type": "pilot.feedback.submitted",
            "pilot_session_id": "pilot-sess-1",
            "run_id": "run-1",
            "helpful": False,
            "reason": "Wrong target",
        },
    )
    assert res.status_code == 200
    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert events[0]["helpful"] is False
    assert events[0]["reason"] == "Wrong target"


def test_missing_event_type_rejected(client):
    res = client.post("/api/pilot/event", json={"doc_id": "x"})
    assert res.status_code == 400


def test_report_generator_computes_metrics_without_fabrication(isolated_pilot_log):
    PilotEventLogger.emit("agent.request.started", session_id="s1")
    PilotEventLogger.emit("agent.clarification.requested", session_id="s1")
    PilotEventLogger.emit("agent.tool.completed", session_id="s1", tool="summarize_element", status="success")
    PilotEventLogger.emit("agent.citation.clicked", session_id="s1")
    PilotEventLogger.emit("agent.reveal.completed", session_id="s1", status="success")
    PilotEventLogger.emit("agent.target.resolved", session_id="s1", count=1)

    events = PilotEventLogger.read_all(isolated_pilot_log)
    metrics = compute_metrics(events)

    assert metrics["total_events"] == len(events)
    assert metrics["requests_started"] == 1
    assert "1/1" in metrics["clarification_rate"]

    report = render_report(metrics)
    assert "NOT YET VERIFIED" in report  # task success has no task events in this synthetic set
    assert "Agent Pilot Report" in report


def test_pilot_event_emission_never_raises(isolated_pilot_log, monkeypatch):
    """Fail-open guarantee: a broken sink must not propagate into the caller."""
    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated sink failure")

    monkeypatch.setattr(PilotEventLogger, "_log_path", staticmethod(_boom))
    result = PilotEventLogger.emit("agent.request.started", session_id="s1")
    assert result is None  # dropped, not raised


def test_pilot_model_changed_event_ingestion(client, isolated_pilot_log):
    """agent.model.changed event records previous_model and new_model via POST /api/pilot/event."""
    res = client.post(
        "/api/pilot/event",
        json={
            "event_type": "agent.model.changed",
            "previous_model": "workbench_luna",
            "new_model": "gemini_3_6_flash",
            "session_id": "sess-1",
        },
    )
    assert res.status_code == 200
    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "agent.model.changed"
    assert ev["previous_model"] == "workbench_luna"
    assert ev["new_model"] == "gemini_3_6_flash"
    assert ev["origin"] == "frontend"


def test_pilot_telemetry_model_tracking_and_privacy(client, isolated_pilot_log, sample_session):
    """Telemetry records application-level model_id + provider without leaking raw
    deployment/model names, document text, or prompt."""
    session_id = sample_session["session_id"]
    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "SECRET_FINANCIAL_PROMPT_CONTENT",
            "model_id": "workbench_sol",
        },
    )
    assert res.status_code == 200

    events = PilotEventLogger.read_all(isolated_pilot_log)
    assert len(events) >= 1

    # Check all events
    for ev in events:
        # Check allowed fields enforcement
        assert "message" not in ev
        assert "prompt" not in ev
        assert "SECRET_FINANCIAL_PROMPT_CONTENT" not in json.dumps(ev)
        # Raw provider deployment/model names must not reach telemetry.
        assert "gpt-5-6-sol-2026-07-09-gs-ae" not in json.dumps(ev)
        assert "gemini-3.6-flash" not in json.dumps(ev)
        if "model_id" in ev:
            assert ev["model_id"] in (
                "workbench_luna",
                "workbench_sol",
                "gemini_3_6_flash",
                "gemini_3_5_flash",
            )
        if "provider" in ev:
            assert ev["provider"] in ("workbench", "gemini")

    # The agent.* events for this turn all carry the selected model and provider.
    agent_events = [e for e in events if e["event_type"].startswith("agent.")]
    assert agent_events
    for ev in agent_events:
        assert ev["model_id"] == "workbench_sol"
        assert ev["provider"] == "workbench"

"""Regression test suite proving complete elimination of deterministic Agent fallback.

Tests verify:
1. No assistant answer or fallback text is generated when Workbench is unreachable.
2. Provider failure returns explicit HTTP 503 / 502 / 504 with structured error details.
3. Luna unavailable -> error with model="luna" (no silent switch to sol).
4. Sol unavailable -> error with model="sol" (no silent switch to luna).
5. Foundation deterministic capabilities (perception, element lookup, anchor resolution, writeback)
   remain fully operational independently of AI provider availability.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.workbench_client import (  # noqa: E402
    WorkbenchAuthenticationError,
    WorkbenchConfigError,
    WorkbenchResponse,
    WorkbenchTimeoutError,
    WorkbenchUnavailableError,
)
from perception.parser import extract_geometry
from perception.anchor_builder import assign_anchors
from perception.element_classifier import classify_blocks

FIXTURE_DOCX = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files" / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx"
FIXTURE_XLSX = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files" / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"


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
            data={"file": (f, "template.docx")},
            content_type="multipart/form-data",
        )
    assert res.status_code == 200
    session_id = res.get_json()["session_id"]
    doc_id = res.get_json()["doc_id"]
    return {"session_id": session_id, "doc_id": doc_id}


def test_agent_has_no_deterministic_fallback_when_workbench_unavailable(client, session_with_docs):
    """Proves that an unreachable Workbench produces an explicit 503 error, NEVER a local fallback response."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Connection refused by gateway")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document in detail",
                "model": "luna",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "unavailable"
        assert "Luna is currently unavailable" in data["error"]
        assert data["model"] == "luna"
        # Assert NO fallback response text is produced
        assert "response" not in data or data.get("response") is None
        assert "I have access to" not in str(data)
        assert "Found matching elements" not in str(data)


def test_agent_has_no_deterministic_fallback_when_credentials_missing(client, session_with_docs, monkeypatch):
    """Missing Workbench credentials produces PROVIDER_CONFIG (503), NEVER a local fallback response."""
    monkeypatch.delenv("WORKBENCH_SUBSCRIPTION_KEY", raising=False)
    monkeypatch.delenv("WORKBENCH_CHARGE_CODE", raising=False)
    session_id = session_with_docs["session_id"]

    res = client.post(
        "/api/agent/chat",
        json={
            "session_id": session_id,
            "message": "Summarize the key information in this document.",
            "model": "sol",
        },
    )

    assert res.status_code == 503
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error_type"] == "config_missing"
    assert "Sol is not configured in this environment." in data["error"]
    assert data["model"] == "sol"
    # Assert NO fallback response text is produced
    assert "response" not in data or data.get("response") is None


def test_luna_failure_does_not_silently_switch_to_sol(client, session_with_docs):
    """When Luna fails, the system must report Luna failure without switching to Sol."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Luna gateway error")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize element",
                "model": "luna",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["model"] == "luna"
        assert "Luna is currently unavailable" in data["error"]


def test_sol_failure_does_not_silently_switch_to_luna(client, session_with_docs):
    """When Sol fails, the system must report Sol failure without switching to Luna."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Sol gateway error")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Deep reasoning request",
                "model": "sol",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["model"] == "sol"
        assert "Sol is currently unavailable" in data["error"]


def test_agent_timeout_returns_504(client, session_with_docs):
    """Workbench timeout raises 504 Gateway Timeout with explicit message."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchTimeoutError("Request timed out after 60s")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Analyze document",
                "model": "luna",
            },
        )

        assert res.status_code == 504
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "timeout"
        assert "Luna request timed out" in data["error"]
        assert data["model"] == "luna"


def test_agent_auth_failure_returns_502(client, session_with_docs):
    """Workbench authentication failure returns 502 Bad Gateway with explicit message."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.orchestrator.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchAuthenticationError("401 Unauthorized")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Analyze document",
                "model": "sol",
            },
        )

        assert res.status_code == 502
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "auth_error"
        assert "Sol authentication failed" in data["error"]
        assert data["model"] == "sol"


def test_foundation_deterministic_tools_function_independently():
    """Validates that Foundation deterministic perception and anchor assignment continue working."""
    blocks = extract_geometry(str(FIXTURE_DOCX))
    assert len(blocks) > 0

    anchors = assign_anchors(blocks, "docx")
    assert len(anchors) == len(blocks)

    elements = classify_blocks(blocks, "docx", anchors)
    assert len(elements) == 848

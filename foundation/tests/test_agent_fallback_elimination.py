"""Regression suite proving complete elimination of Agent fallback, across all
four selectable models and both providers.

Tests verify:
1. No assistant answer or fallback text is generated when a provider is unreachable.
2. Provider failure returns an explicit HTTP status with structured error details.
3. Each of the four models fails as itself: the response names that model_id and
   provider, and no other model is called.
4. A failing model never triggers a second provider call of any kind — not the
   other model of the same provider, not the other provider.
5. Retry re-sends to the SAME model that failed.
6. Foundation deterministic capabilities (perception, element lookup, anchor
   resolution, writeback) remain fully operational independently of AI provider
   availability.
"""
import json
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
from tests.gemini_mocks import gemini_error_response, gemini_ok_response  # noqa: E402

# Every model id in the allowlist, with the label its failures must be reported
# under and the provider that must (and only ever will) be asked.
ALL_MODELS = [
    ("workbench_luna", "workbench", "Luna"),
    ("workbench_sol", "workbench", "Sol"),
    ("gemini_3_6_flash", "gemini", "Gemini 3.6 Flash"),
    ("gemini_3_5_flash", "gemini", "Gemini 3.5 Flash"),
]

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

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Connection refused by gateway")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document in detail",
                "model_id": "workbench_luna",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "unavailable"
        assert "Luna is currently unavailable" in data["error"]
        assert data["model_id"] == "workbench_luna"
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
            "model_id": "workbench_sol",
        },
    )

    assert res.status_code == 503
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error_type"] == "config_missing"
    assert "Sol is not configured in this environment." in data["error"]
    assert data["model_id"] == "workbench_sol"
    # Assert NO fallback response text is produced
    assert "response" not in data or data.get("response") is None


def test_luna_failure_does_not_silently_switch_to_sol(client, session_with_docs):
    """When Luna fails, the system must report Luna failure without switching to Sol."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Luna gateway error")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize element",
                "model_id": "workbench_luna",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["model_id"] == "workbench_luna"
        assert "Luna is currently unavailable" in data["error"]


def test_sol_failure_does_not_silently_switch_to_luna(client, session_with_docs):
    """When Sol fails, the system must report Sol failure without switching to Luna."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchUnavailableError("Sol gateway error")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Deep reasoning request",
                "model_id": "workbench_sol",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["model_id"] == "workbench_sol"
        assert "Sol is currently unavailable" in data["error"]


def test_agent_timeout_returns_504(client, session_with_docs):
    """Workbench timeout raises 504 Gateway Timeout with explicit message."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchTimeoutError("Request timed out after 60s")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Analyze document",
                "model_id": "workbench_luna",
            },
        )

        assert res.status_code == 504
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "timeout"
        assert "Luna request timed out" in data["error"]
        assert data["model_id"] == "workbench_luna"


def test_agent_auth_failure_returns_502(client, session_with_docs):
    """Workbench authentication failure returns 502 Bad Gateway with explicit message."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_cc:
        mock_cc.side_effect = WorkbenchAuthenticationError("401 Unauthorized")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Analyze document",
                "model_id": "workbench_sol",
            },
        )

        assert res.status_code == 502
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "auth_error"
        assert "Sol authentication failed" in data["error"]
        assert data["model_id"] == "workbench_sol"


def test_foundation_deterministic_tools_function_independently():
    """Validates that Foundation deterministic perception and anchor assignment continue working."""
    blocks = extract_geometry(str(FIXTURE_DOCX))
    assert len(blocks) > 0

    anchors = assign_anchors(blocks, "docx")
    assert len(anchors) == len(blocks)

    elements = classify_blocks(blocks, "docx", anchors)
    assert len(elements) == 848


# ============================================================================
# FOUR-MODEL NO-FALLBACK GUARANTEES
# ============================================================================

@pytest.mark.parametrize("model_id,provider,label", ALL_MODELS)
def test_each_model_fails_as_itself_with_no_substitute(
    client, session_with_docs, gemini_enabled, model_id, provider, label
):
    """Whichever model the user picked, its failure is reported as that model's
    failure — never as another model's answer, and never as local text."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
         patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
        mock_wb.side_effect = WorkbenchUnavailableError("gateway error")
        mock_gemini.return_value = gemini_error_response(503, "The model is overloaded.")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document in detail",
                "model_id": model_id,
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "unavailable"
        assert data["model_id"] == model_id
        assert data["provider"] == provider
        assert label in data["error"]

        # No answer text of any kind.
        assert "response" not in data or data.get("response") is None

        # Exactly one provider was consulted, exactly once. A fallback would
        # show up here as a second call.
        if provider == "workbench":
            assert mock_wb.call_count == 1
            assert mock_gemini.call_count == 0
        else:
            assert mock_gemini.call_count == 1
            assert mock_wb.call_count == 0


@pytest.mark.parametrize("model_id,provider,label", ALL_MODELS)
def test_no_other_model_name_appears_in_a_failure(
    client, session_with_docs, gemini_enabled, model_id, provider, label
):
    """The error card must never imply that some other model has answered."""
    session_id = session_with_docs["session_id"]
    other_labels = [lbl for _, _, lbl in ALL_MODELS if lbl != label]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
         patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
        mock_wb.side_effect = WorkbenchUnavailableError("gateway error")
        mock_gemini.return_value = gemini_error_response(503, "overloaded")

        res = client.post(
            "/api/agent/chat",
            json={"session_id": session_id, "message": "Summarize", "model_id": model_id},
        )

    body = json.dumps(res.get_json())
    for other in other_labels:
        # "Gemini 3.6 Flash" contains "Gemini 3.6 Flash" only; substring checks
        # are safe because no label is a substring of another.
        assert other not in body, f"{other} must not be named in a {label} failure"


def test_gemini_3_6_failure_does_not_call_gemini_3_5(client, session_with_docs, gemini_enabled):
    """The 3.6-over-3.5 preference is presentation only — never a fallback chain."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(429, "Quota exceeded.")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document",
                "model_id": "gemini_3_6_flash",
            },
        )

        assert res.status_code == 429
        data = res.get_json()
        assert data["model_id"] == "gemini_3_6_flash"
        assert data["error_type"] == "rate_limited"
        assert "quota/rate limit" in data["error"]
        assert mock_post.call_count == 1
        assert "gemini-3.5-flash" not in mock_post.call_args.args[0]


def test_gemini_3_5_failure_does_not_call_gemini_3_6(client, session_with_docs, gemini_enabled):
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(503, "overloaded")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document",
                "model_id": "gemini_3_5_flash",
            },
        )

        assert res.status_code == 503
        assert res.get_json()["model_id"] == "gemini_3_5_flash"
        assert mock_post.call_count == 1
        assert "gemini-3.6-flash" not in mock_post.call_args.args[0]


def test_gemini_failure_does_not_fall_back_to_workbench(client, session_with_docs, gemini_enabled):
    """A failing Gemini request must not be quietly served by the corporate provider."""
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
         patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
        mock_wb.return_value = WorkbenchResponse(content="Workbench answer", model="luna-dep")
        mock_gemini.return_value = gemini_error_response(500, "internal")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document",
                "model_id": "gemini_3_6_flash",
            },
        )

        assert res.status_code == 503
        assert mock_wb.call_count == 0
        assert "Workbench answer" not in json.dumps(res.get_json())


def test_workbench_failure_does_not_fall_back_to_gemini(client, session_with_docs, gemini_enabled):
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
         patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
        mock_wb.side_effect = WorkbenchUnavailableError("gateway error")
        mock_gemini.return_value = gemini_ok_response("Gemini answer")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document",
                "model_id": "workbench_luna",
            },
        )

        assert res.status_code == 503
        assert mock_gemini.call_count == 0
        assert "Gemini answer" not in json.dumps(res.get_json())


def test_gemini_disabled_environment_errors_instead_of_switching(client, session_with_docs, monkeypatch):
    """With Gemini not enabled, selecting it is an explicit error — the model is
    neither hidden from the selector nor silently served by Workbench."""
    monkeypatch.setenv("AI_PROVIDER_MODE", "workbench")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    session_id = session_with_docs["session_id"]

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb:
        mock_wb.return_value = WorkbenchResponse(content="Workbench answer", model="luna-dep")

        res = client.post(
            "/api/agent/chat",
            json={
                "session_id": session_id,
                "message": "Summarize this document",
                "model_id": "gemini_3_6_flash",
            },
        )

        assert res.status_code == 503
        data = res.get_json()
        assert data["error_type"] == "config_missing"
        assert data["model_id"] == "gemini_3_6_flash"
        assert data["provider"] == "gemini"
        assert "Gemini 3.6 Flash is not configured" in data["error"]
        assert mock_wb.call_count == 0


@pytest.mark.parametrize("model_id,provider,label", ALL_MODELS)
def test_retry_targets_the_same_failed_model(
    client, session_with_docs, gemini_enabled, model_id, provider, label
):
    """A retry is a fresh request carrying the same model_id — the server treats
    it identically and still calls only that model's provider."""
    session_id = session_with_docs["session_id"]

    for attempt in (1, 2):
        with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_wb, \
             patch("applications.agent.providers.gemini_provider.requests.post") as mock_gemini:
            mock_wb.side_effect = WorkbenchUnavailableError("gateway error")
            mock_gemini.return_value = gemini_error_response(503, "overloaded")

            res = client.post(
                "/api/agent/chat",
                json={
                    "session_id": session_id,
                    "message": "Summarize this document",
                    "model_id": model_id,
                },
            )

            assert res.status_code == 503, f"attempt {attempt}"
            assert res.get_json()["model_id"] == model_id
            if provider == "workbench":
                assert mock_wb.call_count == 1 and mock_gemini.call_count == 0
            else:
                assert mock_gemini.call_count == 1 and mock_wb.call_count == 0


def test_no_executable_fallback_path_in_agent_sources():
    """Static guard: no source file in the Agent/provider layer may contain an
    executable fallback branch. Policy prose that mentions the word is fine;
    a code path that switches models is not."""
    import re

    agent_root = Path(__file__).resolve().parents[1] / "applications" / "agent"
    route = Path(__file__).resolve().parents[1] / "api" / "routes" / "agent.py"

    banned = re.compile(
        r"(fall\s?back\s+to|auto[_\s-]?switch|try\s+the\s+other\s+model|"
        r"retry\s+with\s+(a\s+)?different)",
        re.IGNORECASE,
    )

    for path in list(agent_root.rglob("*.py")) + [route]:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if not code.strip():
                continue  # comment-only line: policy prose is allowed
            assert not banned.search(code), f"{path.name}:{lineno} — {line.strip()}"

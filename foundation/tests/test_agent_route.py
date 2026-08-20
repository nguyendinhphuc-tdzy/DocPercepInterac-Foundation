"""Unit tests for the Agent route and Workbench client:
  - POST /api/agent/chat (api/routes/agent.py)
  - applications/workbench_client.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.workbench_client import (  # noqa: E402
    WorkbenchApiError,
    WorkbenchAuthenticationError,
    WorkbenchConfigError,
    WorkbenchResponse,
    WorkbenchTimeoutError,
    WorkbenchUnavailableError,
    chat_completion,
)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_agent_chat_missing_message(client):
    res = client.post("/api/agent/chat", json={})
    assert res.status_code == 400
    assert "Message is required" in res.get_json()["error"]


def test_agent_chat_missing_credentials_returns_503(client, monkeypatch):
    monkeypatch.delenv("WORKBENCH_SUBSCRIPTION_KEY", raising=False)
    monkeypatch.delenv("WORKBENCH_CHARGE_CODE", raising=False)

    res = client.post("/api/agent/chat", json={"message": "Summarize this document"})
    assert res.status_code == 503
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error_type"] == "config_missing"
    assert "Luna is not configured in this environment." in data["error"]
    assert data["model_id"] == "workbench_luna"


def test_agent_chat_sol_missing_credentials_returns_503(client, monkeypatch):
    monkeypatch.delenv("WORKBENCH_SUBSCRIPTION_KEY", raising=False)
    monkeypatch.delenv("WORKBENCH_CHARGE_CODE", raising=False)

    res = client.post("/api/agent/chat", json={"message": "Deep analysis", "model_id": "workbench_sol"})
    assert res.status_code == 503
    data = res.get_json()
    assert data["status"] == "error"
    assert data["error_type"] == "config_missing"
    assert "Sol is not configured in this environment." in data["error"]
    assert data["model_id"] == "workbench_sol"


def test_agent_chat_provider_unavailable_returns_503(client):
    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_chat:
        mock_chat.side_effect = WorkbenchUnavailableError("Connection refused")

        res = client.post("/api/agent/chat", json={"message": "Analyze data", "model_id": "workbench_luna"})
        assert res.status_code == 503
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "unavailable"
        assert "Luna is currently unavailable" in data["error"]
        assert data["model_id"] == "workbench_luna"


def test_agent_chat_timeout_returns_504(client):
    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_chat:
        mock_chat.side_effect = WorkbenchTimeoutError("Timed out")

        res = client.post("/api/agent/chat", json={"message": "Analyze data", "model_id": "workbench_sol"})
        assert res.status_code == 504
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "timeout"
        assert "Sol request timed out" in data["error"]
        assert data["model_id"] == "workbench_sol"


def test_agent_chat_auth_failure_returns_502(client):
    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_chat:
        mock_chat.side_effect = WorkbenchAuthenticationError("401 Unauthorized")

        res = client.post("/api/agent/chat", json={"message": "Analyze data", "model_id": "workbench_luna"})
        assert res.status_code == 502
        data = res.get_json()
        assert data["status"] == "error"
        assert data["error_type"] == "auth_error"
        assert "Luna authentication failed" in data["error"]
        assert data["model_id"] == "workbench_luna"


def test_agent_chat_success_mocked_luna(client, monkeypatch):
    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.setenv("WORKBENCH_CHARGE_CODE", "fake-code")

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_chat:
        mock_chat.return_value = WorkbenchResponse(
            content="Document contains 4 financial tables.",
            model="gpt-5-6-luna-2026-07-09-gs-ae",
            usage={"prompt_tokens": 10, "completion_tokens": 8},
        )

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "What is in this document?",
                "model_id": "workbench_luna",
                "context": {
                    "file_names": ["report.docx", "data.xlsx"],
                    "element_count": 42,
                },
            },
        )

        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["response"] == "Document contains 4 financial tables."
        assert data["model_id"] == "workbench_luna"
        assert len(data["steps"]) > 0
        assert data["run_id"] is not None


def test_agent_chat_success_mocked_sol(client, monkeypatch):
    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.setenv("WORKBENCH_CHARGE_CODE", "fake-code")

    with patch("applications.agent.providers.workbench_provider.chat_completion") as mock_chat:
        mock_chat.return_value = WorkbenchResponse(
            content="Deep multi-step financial analysis completed.",
            model="gpt-5-6-sol-2026-07-09-gs-ae",
            usage={"prompt_tokens": 20, "completion_tokens": 16},
        )

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "Perform complex tax comparison.",
                "model_id": "workbench_sol",
                "context": {
                    "file_names": ["report.docx", "data.xlsx"],
                    "element_count": 42,
                },
            },
        )

        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["response"] == "Deep multi-step financial analysis completed."
        assert data["model_id"] == "workbench_sol"


def test_workbench_client_raises_without_charge_code(monkeypatch):
    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.delenv("WORKBENCH_CHARGE_CODE", raising=False)

    with pytest.raises(WorkbenchConfigError) as exc_info:
        chat_completion([{"role": "user", "content": "test"}])
    assert "WORKBENCH_CHARGE_CODE" in str(exc_info.value)

"""Unit tests for the Agent route and Workbench client:
  - POST /api/agent/chat (api/routes/agent.py)
  - applications/gpts/workbench_client.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.app import create_app  # noqa: E402
from applications.gpts.workbench_client import (  # noqa: E402
    WorkbenchConfigError,
    WorkbenchResponse,
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
    assert "WORKBENCH_SUBSCRIPTION_KEY" in data["error"]
    assert "Agent is not configured" in data["response"]


def test_agent_chat_success_mocked(client, monkeypatch):
    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.setenv("WORKBENCH_CHARGE_CODE", "fake-code")

    with patch("api.routes.agent.chat_completion") as mock_chat:
        mock_chat.return_value = WorkbenchResponse(
            content="Document contains 4 financial tables.",
            model="gpt-5-4-2026-03-05-gs-ae",
            usage={"prompt_tokens": 10, "completion_tokens": 8},
        )

        res = client.post(
            "/api/agent/chat",
            json={
                "message": "What is in this document?",
                "context": {
                    "file_names": ["report.docx", "data.xlsx"],
                    "element_count": 42,
                    "mapped_count": 5,
                    "mapped_summary": [
                        {"target_anchor": "table:0:0:0", "target_value": "100", "confidence": 0.99}
                    ],
                },
            },
        )

        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "success"
        assert data["response"] == "Document contains 4 financial tables."
        assert len(data["steps"]) > 0
        assert data["run_id"] is not None

        # Verify system prompt was constructed with context
        call_args = mock_chat.call_args[1]["messages"]
        system_msg = next(m["content"] for m in call_args if m["role"] == "system")
        assert "report.docx" in system_msg
        assert "Total extracted elements: 42" in system_msg


def test_workbench_client_raises_without_charge_code(monkeypatch):
    monkeypatch.setenv("WORKBENCH_SUBSCRIPTION_KEY", "fake-key")
    monkeypatch.delenv("WORKBENCH_CHARGE_CODE", raising=False)

    with pytest.raises(WorkbenchConfigError) as exc_info:
        chat_completion([{"role": "user", "content": "test"}])
    assert "WORKBENCH_CHARGE_CODE" in str(exc_info.value)

"""POST /api/agent/chat — AI Agent endpoint that proxies user requests
to the KPMG Workbench, enriched with generic Foundation document context.

Architecture note: this route calls applications/workbench_client.py — a
shared, use-case-agnostic Workbench proxy (NOT applications/gpts/, which is
GTPS-specific). It does NOT import from perception/, output/, or eval/, and
must not import anything from applications/gpts/ either: the context this
route builds is deliberately generic (file names + element counts), never
GTPS-shaped (no source/target/mapped fields).
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.agent.orchestrator import AgentOrchestrator  # noqa: E402
from applications.agent.action_executor import ActionExecutor  # noqa: E402
from applications.workbench_client import (  # noqa: E402
    WorkbenchApiError,
    WorkbenchConfigError,
)

agent_bp = Blueprint("agent", __name__)


@agent_bp.post("/api/agent/chat")
def agent_chat():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    session_id = body.get("session_id")
    context = body.get("context", {})

    try:
        response_model = AgentOrchestrator.handle_chat(
            message=message,
            session_id=session_id,
            context_input=context,
        )
        return jsonify(response_model.model_dump(mode="json"))
    except WorkbenchConfigError as exc:
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Agent is not configured: {exc}",
            "run_id": None,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 503
    except WorkbenchApiError as exc:
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Workbench API error: {exc}",
            "run_id": None,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 502
    except Exception as exc:
        return jsonify({
            "error": f"Unexpected error: {exc}",
            "status": "error",
            "response": f"An unexpected error occurred: {exc}",
            "run_id": None,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 500


@agent_bp.post("/api/agent/action/execute")
def execute_action():
    """Executes a user-confirmed governed action proposal.
    Payload: {"session_id": "...", "action_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    action_id = body.get("action_id")

    if not session_id:
        return jsonify({"error": "session_id is required."}), 400
    if not action_id:
        return jsonify({"error": "action_id is required."}), 400

    try:
        result = ActionExecutor.execute_confirmed_action(session_id, action_id)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc), "status": "rejected"}), 400
    except Exception as exc:
        return jsonify({"error": f"Execution failed: {exc}", "status": "error"}), 500


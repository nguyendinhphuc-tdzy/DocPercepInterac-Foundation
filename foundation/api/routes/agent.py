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

from applications.agent.models import (  # noqa: E402
    AGENT_MODELS,
    DEFAULT_MODEL,
    AgentModelId,
    get_model_key,
    resolve_agent_model,
)
from applications.agent.orchestrator import AgentOrchestrator  # noqa: E402
from applications.agent.action_executor import ActionExecutor  # noqa: E402
from applications.pilot.event_log import PilotEventLogger  # noqa: E402
from applications.workbench_client import (  # noqa: E402
    WorkbenchApiError,
    WorkbenchConfigError,
)

agent_bp = Blueprint("agent", __name__)

_CLARIFY_INTENTS = {"clarify_target", "clarify_document", "clarify_comparison"}


@agent_bp.get("/api/agent/models")
def get_available_models():
    """Returns the fixed allowlist of user-selectable Agent models."""
    return jsonify({
        "default": DEFAULT_MODEL,
        "models": [
            {
                "id": "luna",
                "name": "Luna",
                "description": "Fast · Everyday tasks",
                "is_default": True,
            },
            {
                "id": "sol",
                "name": "Sol",
                "description": "Deep reasoning · Complex analysis",
                "is_default": False,
            },
        ],
    })


@agent_bp.post("/api/agent/chat")
def agent_chat():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    session_id = body.get("session_id")
    context = body.get("context", {})
    raw_model = body.get("model")

    # Validate model against strict server-side allowlist (reject unknown/unsupported)
    try:
        if raw_model is not None and not str(raw_model).strip():
            return jsonify({
                "error": f"Invalid model '{raw_model}'. Supported models: {sorted(AGENT_MODELS.keys())}",
                "status": "error",
            }), 400
        model_deployment = resolve_agent_model(raw_model)
        model_key: AgentModelId = get_model_key(raw_model)
    except ValueError as exc:
        return jsonify({"error": str(exc), "status": "error"}), 400

    PilotEventLogger.emit(
        "agent.request.started",
        session_id=session_id,
        message_length=len(message),
        has_selection=bool(context.get("selected_element_id")),
        has_active_doc=bool(context.get("active_doc_id")),
        doc_count=len(context.get("file_names") or []),
        model=model_key,
    )

    try:
        response_model = AgentOrchestrator.handle_chat(
            message=message,
            session_id=session_id,
            context_input=context,
            model=model_key,
        )
        run_id = response_model.run_id
        intent = response_model.intent

        PilotEventLogger.emit(
            "agent.intent.resolved",
            session_id=session_id,
            run_id=run_id,
            intent=intent,
            model=model_key,
        )
        PilotEventLogger.emit(
            "agent.tool.selected",
            session_id=session_id,
            run_id=run_id,
            tool=intent,
            model=model_key,
        )
        if intent in _CLARIFY_INTENTS:
            PilotEventLogger.emit(
                "agent.clarification.requested",
                session_id=session_id,
                run_id=run_id,
                intent=intent,
                model=model_key,
            )
        if response_model.citations:
            first = response_model.citations[0]
            PilotEventLogger.emit(
                "agent.target.resolved",
                session_id=session_id,
                run_id=run_id,
                doc_id=first.doc_id,
                element_id=first.element_id,
                count=len(response_model.citations),
                model=model_key,
            )
        if response_model.proposed_actions:
            for action in response_model.proposed_actions:
                PilotEventLogger.emit(
                    "agent.proposal.created",
                    session_id=session_id,
                    run_id=run_id,
                    action_id=action.action_id,
                    doc_id=action.doc_id,
                    element_id=action.element_id,
                    model=model_key,
                )
        PilotEventLogger.emit(
            "agent.tool.completed",
            session_id=session_id,
            run_id=run_id,
            tool=intent,
            status="success",
            model=model_key,
        )

        return jsonify(response_model.model_dump(mode="json"))
    except WorkbenchConfigError as exc:
        PilotEventLogger.emit(
            "agent.tool.failed", session_id=session_id, error_category="PROVIDER", status="error", model=model_key,
        )
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Agent is not configured: {exc}",
            "run_id": None,
            "model": model_key,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 503
    except WorkbenchApiError as exc:
        PilotEventLogger.emit(
            "agent.tool.failed", session_id=session_id, error_category="PROVIDER", status="error", model=model_key,
        )
        return jsonify({
            "error": str(exc),
            "status": "error",
            "response": f"Workbench API error: {exc}",
            "run_id": None,
            "model": model_key,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 502
    except Exception as exc:
        PilotEventLogger.emit(
            "agent.tool.failed", session_id=session_id, error_category="UNKNOWN", status="error", model=model_key,
        )
        return jsonify({
            "error": f"Unexpected error: {exc}",
            "status": "error",
            "response": f"An unexpected error occurred: {exc}",
            "run_id": None,
            "model": model_key,
            "steps": [],
            "citations": [],
            "proposed_actions": [],
        }), 500


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"
from applications.agent.proposal_store import ProposalStore  # noqa: E402


@agent_bp.post("/api/agent/action/execute")
def execute_action():
    """Executes a user-confirmed governed action proposal.
    Payload: {"session_id": "...", "action_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    action_id = body.get("action_id")

    if not session_id or not action_id:
        return jsonify({"error": "session_id and action_id are required.", "status": "error"}), 400

    session_dir = UPLOAD_ROOT / session_id
    if not session_dir.is_dir():
        return jsonify({"error": "Invalid session or action proposal not found.", "status": "rejected"}), 400

    PilotEventLogger.emit(
        "agent.proposal.confirmed", session_id=session_id, action_id=action_id,
    )
    try:
        result = ActionExecutor.execute_confirmed_action(session_id, action_id)
        PilotEventLogger.emit(
            "agent.write.completed",
            session_id=session_id,
            action_id=action_id,
            doc_id=result.get("doc_id"),
            element_id=result.get("element_id"),
        )
        return jsonify(result)
    except ValueError as exc:
        PilotEventLogger.emit(
            "agent.write.failed",
            session_id=session_id,
            action_id=action_id,
            error_category="GOVERNANCE",
        )
        return jsonify({"error": str(exc), "status": "rejected"}), 400
    except Exception as exc:
        PilotEventLogger.emit(
            "agent.write.failed",
            session_id=session_id,
            action_id=action_id,
            error_category="WRITEBACK",
        )
        return jsonify({"error": f"Execution failed: {exc}", "status": "error"}), 500


@agent_bp.post("/api/agent/action/reject")
def reject_action():
    """Rejects a proposed action on the server.
    Payload: {"session_id": "...", "action_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    action_id = body.get("action_id")

    if not session_id or not action_id:
        return jsonify({"error": "session_id and action_id are required.", "status": "error"}), 400

    session_dir = UPLOAD_ROOT / session_id
    if not session_dir.is_dir():
        return jsonify({"error": "Invalid session or action proposal not found.", "status": "rejected"}), 400

    proposal = ProposalStore.get_proposal(session_id, action_id)
    if not proposal:
        return jsonify({"error": f"Action proposal '{action_id}' not found or has expired.", "status": "rejected"}), 404

    if proposal.status != "proposed":
        return jsonify({
            "error": f"Action proposal '{action_id}' cannot be rejected (current status: '{proposal.status}').",
            "status": proposal.status,
        }), 400

    try:
        ProposalStore.update_proposal_status(session_id, action_id, "rejected")
        PilotEventLogger.emit(
            "agent.proposal.rejected", session_id=session_id, action_id=action_id,
        )
        return jsonify({"status": "rejected", "action_id": action_id})
    except Exception as exc:
        return jsonify({"error": f"Failed to reject proposal: {exc}", "status": "error"}), 500


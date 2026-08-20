"""POST /api/agent/chat — AI Agent endpoint that runs the user's request
against the model they selected, enriched with generic Foundation document
context.

Architecture note: this route calls the Agent orchestrator, which reaches
models only through applications/agent/providers/ (Workbench or Gemini). It
does NOT import from perception/, output/, or eval/, and must not import
anything from applications/gpts/ either: the context this route builds is
deliberately generic (file names + element counts), never GTPS-shaped (no
source/target/mapped fields).

MODEL SELECTION CONTRACT
  - The frontend sends an application-level model id only. Raw provider
    deployment names are never accepted from, nor returned to, the browser.
  - The id is validated against the strict four-entry allowlist in
    applications/agent/models.py. Anything else is HTTP 400.
  - If the selected model's provider fails for any reason — unconfigured,
    unauthenticated, unavailable, timed out, rate limited, quota exhausted,
    invalid request, malformed response — this route returns an explicit error
    naming that model. It never retries against a different model, never
    switches provider, and never returns locally generated answer text. The
    user is the only thing that can change the model.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.agent.models import (  # noqa: E402
    AGENT_MODEL_ORDER,
    AGENT_MODELS,
    DEFAULT_MODEL,
    AgentModelSpec,
    resolve_agent_model,
)
from applications.agent.orchestrator import AgentOrchestrator  # noqa: E402
from applications.agent.action_executor import ActionExecutor  # noqa: E402
from applications.agent.providers import ProviderError  # noqa: E402
from applications.pilot.event_log import PilotEventLogger  # noqa: E402

agent_bp = Blueprint("agent", __name__)

_CLARIFY_INTENTS = {"clarify_target", "clarify_document", "clarify_comparison"}


@agent_bp.get("/api/agent/models")
def get_available_models():
    """Returns the fixed allowlist of user-selectable Agent models.

    Order is presentation only. Gemini 3.6 Flash sits above Gemini 3.5 Flash
    because it is the preferred Gemini option for local/demo use — that is a
    product preference, not a routing or fallback rule.
    """
    return jsonify({
        "default": DEFAULT_MODEL,
        "models": [
            {
                "id": spec.model_id,
                "name": spec.label,
                "description": spec.description,
                "provider": spec.provider,
                "group": spec.group,
                "is_default": spec.model_id == DEFAULT_MODEL,
            }
            for spec in (AGENT_MODELS[m] for m in AGENT_MODEL_ORDER)
        ],
    })


# User-facing copy for each normalized provider error. Keyed by
# ProviderError.error_type so a new provider inherits the whole vocabulary by
# mapping onto it, with no new UI strings. Deliberately free of API keys,
# endpoints, stack traces and raw provider dumps.
_ERROR_TEMPLATES: dict[str, str] = {
    "config_missing": "{label} is not configured in this environment.",
    "auth_error": "{label} authentication failed. Please verify provider credentials.",
    "timeout": "{label} request timed out. Please try again.",
    "rate_limited": (
        "{label} is temporarily unavailable because its current API "
        "quota/rate limit was reached."
    ),
    "unavailable": "{label} is currently unavailable because the AI service could not be reached.",
    "invalid_request": "{label} rejected the request as invalid.",
    "malformed_response": "{label} returned a response that could not be read.",
    "content_blocked": "{label} declined to answer this request under its safety policy.",
    "unsupported_operation": "{label} does not support this operation.",
    "unexpected": "An unexpected error occurred while communicating with {label}.",
}


def _provider_error_response(spec: AgentModelSpec, error_type: str, http_status: int,
                             session_id, error_category: str):
    """Build the explicit single-model failure payload.

    The payload names only the model the user selected. There is no `response`
    field and no assistant text of any kind, so the client cannot mistake a
    failure for an answer, and no other model is named as having answered.
    """
    template = _ERROR_TEMPLATES.get(error_type, _ERROR_TEMPLATES["unexpected"])
    PilotEventLogger.emit(
        "agent.tool.failed",
        session_id=session_id,
        error_category=error_category,
        error_type=error_type,
        request_status="error",
        status="error",
        model_id=spec.model_id,
        provider=spec.provider,
    )
    return jsonify({
        "error": template.format(label=spec.label),
        "status": "error",
        "error_type": error_type,
        "model_id": spec.model_id,
        "provider": spec.provider,
        "run_id": None,
        "steps": [],
        "citations": [],
        "proposed_actions": [],
    }), http_status


@agent_bp.post("/api/agent/chat")
def agent_chat():
    body = request.get_json(silent=True) or {}
    message = body.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    session_id = body.get("session_id")
    context = body.get("context", {})
    # `model_id` is the field name the rest of the system uses; `model` is
    # accepted as the legacy request key. Both carry an application-level id
    # and go through the same strict allowlist.
    raw_model = body.get("model_id", body.get("model"))

    # Strict server-side allowlist. An absent id means "the user did not
    # choose" and resolves to the documented default; anything present but
    # unrecognized is rejected outright rather than coerced to a working model.
    try:
        if raw_model is not None and not str(raw_model).strip():
            raw_model = ""  # empty string is an explicit invalid value, not "absent"
        spec: AgentModelSpec = resolve_agent_model(raw_model)
    except ValueError as exc:
        return jsonify({"error": str(exc), "status": "error"}), 400

    PilotEventLogger.emit(
        "agent.request.started",
        session_id=session_id,
        message_length=len(message),
        has_selection=bool(context.get("selected_element_id")),
        has_active_doc=bool(context.get("active_doc_id")),
        doc_count=len(context.get("file_names") or []),
        request_status="started",
        model_id=spec.model_id,
        provider=spec.provider,
    )

    telemetry = {"model_id": spec.model_id, "provider": spec.provider}

    try:
        response_model = AgentOrchestrator.handle_chat(
            message=message,
            session_id=session_id,
            context_input=context,
            model=spec.model_id,
        )
        run_id = response_model.run_id
        intent = response_model.intent

        PilotEventLogger.emit(
            "agent.intent.resolved",
            session_id=session_id,
            run_id=run_id,
            intent=intent,
            **telemetry,
        )
        PilotEventLogger.emit(
            "agent.tool.selected",
            session_id=session_id,
            run_id=run_id,
            tool=intent,
            **telemetry,
        )
        if intent in _CLARIFY_INTENTS:
            PilotEventLogger.emit(
                "agent.clarification.requested",
                session_id=session_id,
                run_id=run_id,
                intent=intent,
                **telemetry,
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
                **telemetry,
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
                    **telemetry,
                )
        PilotEventLogger.emit(
            "agent.tool.completed",
            session_id=session_id,
            run_id=run_id,
            tool=intent,
            status="success",
            request_status="success",
            **telemetry,
        )

        return jsonify(response_model.model_dump(mode="json"))
    except ProviderError as exc:
        # Every provider failure lands here as one normalized error carrying the
        # error_type and HTTP status to surface. No branch of this handler tries
        # another model, another provider, or a locally generated answer.
        return _provider_error_response(
            spec,
            exc.error_type,
            exc.http_status,
            session_id,
            f"PROVIDER_{exc.error_type.upper()}",
        )
    except Exception:
        return _provider_error_response(
            spec, "unexpected", 500, session_id, "UNKNOWN",
        )


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


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
import time
import uuid
from pathlib import Path

from typing import Optional

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.agent.models import (  # noqa: E402
    AGENT_MODEL_ORDER,
    AGENT_MODELS,
    DEFAULT_MODEL,
    AgentModelSpec,
    resolve_agent_model,
)
from applications.agent.interaction_context import (  # noqa: E402
    InteractionContextError,
    InteractionContextVerifier,
)
from applications.agent.models import AgentResponse, AgentStep  # noqa: E402
from applications.agent.orchestrator import AgentOrchestrator  # noqa: E402
from applications.agent.rollforward_agent import RollForwardAgentHandler  # noqa: E402
from applications.agent.rollforward_plan_store import (  # noqa: E402
    RollForwardApprovalError,
    RollForwardApprovalService,
)
from applications.agent.action_executor import ActionExecutor  # noqa: E402
from applications.agent.providers import ProviderError  # noqa: E402
from applications.pilot.event_log import PilotEventLogger  # noqa: E402

agent_bp = Blueprint("agent", __name__)

_CLARIFY_INTENTS = {"clarify_target", "clarify_document", "clarify_comparison"}

# Intents answered entirely from server state. A turn with one of these must not
# have consulted a model — that is the whole point of routing them deterministically.
DETERMINISTIC_INTENTS = {"roll_forward", "roll_forward_status"}


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

    # Verify the selection BEFORE anything else runs: an unverifiable selection
    # is an explicit 4xx, never a silently ignored one.
    try:
        interaction = InteractionContextVerifier.verify(
            body.get("interaction_context"), session_id=session_id, user_id=_get_user_id())
    except InteractionContextError as exc:
        PilotEventLogger.emit(
            "agent.request.context",
            session_id=session_id,
            selection_valid=False,
            error_type=exc.code,
            request_status="error",
        )
        return jsonify(exc.to_payload()), 400

    PilotEventLogger.emit(
        "agent.request.context",
        session_id=session_id,
        selection_valid=True,
        **interaction.telemetry(),
    )

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
        # Wall-clock for the whole turn. A deterministic workflow answer should
        # be milliseconds; only a turn that actually consults a model should cost
        # seconds. Both are reported, so the difference is visible instead of
        # inferred.
        turn_started = time.perf_counter()
        response_model = AgentOrchestrator.handle_chat(
            message=message,
            session_id=session_id,
            context_input=context,
            model=spec.model_id,
            user_id=_get_user_id(),
            interaction=interaction,
        )
        total_ms = round((time.perf_counter() - turn_started) * 1000, 2)
        run_id = response_model.run_id
        intent = response_model.intent

        assessment = response_model.roll_forward_assessment or {}
        PilotEventLogger.emit(
            "agent.timing",
            session_id=session_id,
            run_id=run_id,
            intent=intent,
            total_ms=total_ms,
            llm_used=intent not in DETERMINISTIC_INTENTS,
            stage_timings_ms=assessment.get("timings_ms", {}),
            **telemetry,
        )

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


from adapters.repository import get_repositories  # noqa: E402
from applications.agent.proposal_store import ProposalStore  # noqa: E402


def _get_user_id() -> str:
    return request.headers.get("X-User-Id", "anonymous")


@agent_bp.post("/api/agent/action/execute")
def execute_action():
    """Executes a user-confirmed governed action proposal.
    Payload: {"session_id": "...", "action_id": "..."}
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    action_id = body.get("action_id")
    user_id = _get_user_id()

    if not session_id or not action_id:
        return jsonify({"error": "session_id and action_id are required.", "status": "error"}), 400

    repos = get_repositories()
    proposal = ProposalStore.get_proposal(session_id, action_id, user_id=user_id)
    if not proposal:
        return jsonify({"error": "Invalid session or action proposal not found.", "status": "rejected"}), 400

    PilotEventLogger.emit(
        "agent.proposal.confirmed", session_id=session_id, action_id=action_id,
    )
    try:
        result = ActionExecutor.execute_confirmed_action(session_id, action_id, user_id=user_id)
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
    user_id = _get_user_id()

    if not session_id or not action_id:
        return jsonify({"error": "session_id and action_id are required.", "status": "error"}), 400

    proposal = ProposalStore.get_proposal(session_id, action_id, user_id=user_id)
    if not proposal:
        return jsonify({"error": f"Action proposal '{action_id}' not found or has expired.", "status": "rejected"}), 404

    if proposal.status != "proposed":
        return jsonify({
            "error": f"Action proposal '{action_id}' cannot be rejected (current status: '{proposal.status}').",
            "status": proposal.status,
        }), 400

    try:
        ProposalStore.update_proposal_status(session_id, action_id, "rejected", user_id=user_id)
        PilotEventLogger.emit(
            "agent.proposal.rejected", session_id=session_id, action_id=action_id,
        )
        return jsonify({"status": "rejected", "action_id": action_id})
    except Exception as exc:
        return jsonify({"error": f"Failed to reject proposal: {exc}", "status": "error"}), 500


# ============================================================================
# GOVERNED ROLL-FORWARD APPROVAL
# ============================================================================

@agent_bp.post("/api/agent/rollforward/approve")
def approve_roll_forward():
    """Approve the governed plan for a session and execute it. Nothing else can.

    This is the ONLY route that can produce a roll-forward result. It refuses —
    it never simulates — when there is no governed plan, when the plan no longer
    describes the workflow's documents, or when readiness has regressed. The
    mutation itself is performed by RollForwardOrchestrator, which runs the
    structural writeback, the reconciliation and the full-document validation.

    Payload: {"session_id": "...", "approver": "name@firm", "plan_id": "optional"}
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    approver = (body.get("approver") or "").strip()
    plan_id = body.get("plan_id")
    user_id = _get_user_id()

    if not session_id:
        return jsonify({"error": "session_id is required.", "status": "error"}), 400
    if not approver:
        return jsonify({
            "error": "An approver is required: execution is authorised by a person.",
            "status": "error",
        }), 400

    started = time.perf_counter()
    PilotEventLogger.emit("agent.rollforward.approval.requested",
                          session_id=session_id, approver_supplied=True)

    try:
        report, plan = RollForwardApprovalService.approve_and_execute(
            session_id=session_id, approver=approver, user_id=user_id, plan_id=plan_id)
    except RollForwardApprovalError as exc:
        PilotEventLogger.emit("agent.rollforward.approval.refused",
                              session_id=session_id, reason_category="GOVERNANCE")
        return jsonify({"error": str(exc), "status": "refused"}), 409
    except Exception as exc:
        PilotEventLogger.emit("agent.rollforward.execution.failed",
                              session_id=session_id, error_category="EXECUTION")
        return jsonify({"error": f"Roll-forward execution failed: {exc}",
                        "status": "error"}), 500

    execution_ms = round((time.perf_counter() - started) * 1000, 2)
    output_document = _publish_output_document(session_id, user_id, report)
    result = RollForwardAgentHandler.result_from_report(report, output_document)

    PilotEventLogger.emit(
        "agent.rollforward.execution.completed",
        session_id=session_id,
        execution_id=result.execution_id,
        status=result.status,
        publication_state=result.publication_state,
        reconciliation_status=result.reconciliation_status,
        regions_changed=result.regions_changed,
        execution_ms=execution_ms,
    )

    # The response says "completed" only if the report says so. A failed or
    # unpublished run reports itself as such, with the orchestrator's own status.
    if result.is_complete:
        text = (f"Roll-forward executed. Output document produced "
                f"({result.regions_changed} region(s), {result.cells_updated} cell(s), "
                f"{result.rows_inserted} row(s) inserted). "
                f"Reconciliation: {result.reconciliation_status}.")
    else:
        text = (f"Roll-forward did not complete (status {result.status}, publication "
                f"{result.publication_state}). No output has been published. "
                f"{report.failure_detail}".strip())

    response = AgentResponse(
        response=text,
        status="success",
        run_id=result.execution_id,
        intent="roll_forward",
        steps=[
            AgentStep(label="Verified governed plan against workflow documents", status="done"),
            AgentStep(label=f"Recorded approval by {approver}", status="done"),
            AgentStep(label="Executed structural writeback", status="done"),
            AgentStep(label="Reconciled values against sources", status="done"),
            AgentStep(label="Validated the output document", status="done"),
        ],
        roll_forward_result=result,
        roll_forward_assessment={"stage": "EXECUTED", "plan": plan.preview(),
                                 "execution_ms": execution_ms},
    )
    return jsonify(response.model_dump(mode="json"))


def _publish_output_document(session_id: str, user_id: str, report) -> Optional[dict]:
    """Register the produced document so the user can open and download it.

    Returns None when the run produced no output — which is exactly when the
    result must not read as complete.
    """
    output_path = getattr(report, "output_path", None)
    if not output_path or not Path(output_path).exists():
        return None

    from adapters.storage import get_storage
    from adapters.repository import DocumentRecord, DocumentVersionRecord

    path = Path(output_path)
    doc_id = str(uuid.uuid4())
    data = path.read_bytes()

    storage = get_storage()
    repos = get_repositories()
    repos.sessions.get_or_create(session_id, user_id=user_id)
    stored = storage.save_document(session_id=session_id, doc_id=doc_id, filename=path.name,
                                   data=data, is_patched=False, user_id=user_id)
    repos.documents.save_document(DocumentRecord(
        doc_id=doc_id, session_id=session_id, user_id=user_id,
        original_filename=path.name, format=path.suffix.lstrip("."), status="ready"))
    repos.documents.create_version(DocumentVersionRecord(
        version_id=str(uuid.uuid4()), doc_id=doc_id, session_id=session_id, user_id=user_id,
        version_number=1, sha256=getattr(report, "output_hash", "") or stored.file_hash,
        storage_path=stored.storage_path, is_patched=False, size_bytes=stored.size_bytes))

    return {
        "doc_id": doc_id,
        "filename": path.name,
        "download_url": f"/api/documents/{session_id}/download/{doc_id}",
        "sha256": getattr(report, "output_hash", None),
    }

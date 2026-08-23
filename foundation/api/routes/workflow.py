"""
Workflow intake routes (Phase PROD-UX-1)
========================================
Location: foundation/api/routes/workflow.py

The Access-layer surface for a workflow that has a dedicated structured intake
instead of the generic blank document workspace:

    POST   /api/workflow/sessions
    GET    /api/workflow/<session_id>
    POST   /api/workflow/<session_id>/slots/<slot_id>/assign
    DELETE /api/workflow/<session_id>/slots/<slot_id>/documents/<doc_id>
    POST   /api/workflow/<session_id>/slots/<slot_id>/documents/<doc_id>/review
    GET    /api/workflow/<session_id>/agent-context

Boundary notes
--------------
    * A document is uploaded and perceived by the GENERIC document layer
      (POST /api/documents) exactly as before. This blueprint only ever adds a
      workflow ROLE on top of an already-perceived document — it never uploads,
      never re-perceives and never writes to a document.
    * Every role decision comes from applications/rollforward/workflow_intake.py,
      which derives it from the file's content. Nothing here inspects a filename.
    * No mutation, no plan approval, no execution. The gate this endpoint reports
      is the reason execution stays blocked, not permission to run it.

State is persisted next to the session's uploads as `workflow.json`, alongside
the `manifest.json` the document layer already keeps, so intake survives a page
reload without introducing a new database table this phase.
"""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from adapters.repository import get_repositories  # noqa: E402
from adapters.storage import get_storage  # noqa: E402
from applications.rollforward.workflow_intake import (  # noqa: E402
    SlotId,
    WorkflowIntakeError,
    WorkflowIntakeSession,
    WorkflowType,
)

workflow_bp = Blueprint("workflow", __name__)

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"
STATE_FILENAME = "workflow.json"


# ============================================================================
# SESSION STATE PERSISTENCE
# ============================================================================

def _get_user_id() -> str:
    return request.headers.get("X-User-Id", "anonymous")


def _session_dir(session_id: str) -> Path:
    return UPLOAD_ROOT / secure_filename(session_id)


def _state_path(session_id: str) -> Path:
    return _session_dir(session_id) / STATE_FILENAME


def _load_session(session_id: str) -> Optional[WorkflowIntakeSession]:
    path = _state_path(session_id)
    if not path.exists():
        return None
    try:
        return WorkflowIntakeSession.from_state_dict(
            json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


def _save_session(session: WorkflowIntakeSession) -> None:
    directory = _session_dir(session.session_id)
    directory.mkdir(parents=True, exist_ok=True)
    _state_path(session.session_id).write_text(
        json.dumps(session.state_to_dict(), indent=2), encoding="utf-8")


# ============================================================================
# DOCUMENT RESOLUTION — reuses the generic document layer, never re-perceives
# ============================================================================

def _manifest_entry(session_id: str, doc_id: str) -> Optional[Dict[str, Any]]:
    manifest_path = _session_dir(session_id) / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return manifest.get("documents", {}).get(doc_id)


@contextmanager
def _resolve_document(session_id: str, doc_id: str,
                      user_id: str) -> Iterator[Tuple[Path, Dict[str, Any]]]:
    """Yields (path_on_disk, metadata) for an already-uploaded document.

    Prefers the local session directory the document layer maintains; falls back
    to the storage abstraction's temp-file lifecycle for object-storage backends.
    """
    entry = _manifest_entry(session_id, doc_id)
    if entry is not None:
        stored = _session_dir(session_id) / entry["stored_filename"]
        if stored.exists():
            yield stored, {
                "filename": entry.get("original_filename", stored.name),
                "status": entry.get("status", "ready"),
                "element_count": entry.get("element_count"),
            }
            return

    repos = get_repositories()
    doc = repos.documents.get_document(session_id, doc_id, user_id=user_id)
    if doc is None:
        raise WorkflowIntakeError(f"Document '{doc_id}' is not part of this session.")

    storage = get_storage()
    with storage.get_document_path(session_id, doc_id, is_patched=False,
                                   user_id=user_id) as path:
        yield path, {
            "filename": doc.original_filename,
            "status": doc.status,
            "element_count": doc.element_count,
        }


# ============================================================================
# ROUTES
# ============================================================================

def _parse_slot(raw: str) -> SlotId:
    try:
        return SlotId(raw.upper())
    except ValueError as exc:
        raise WorkflowIntakeError(
            f"Unknown input slot '{raw}'. This workflow has: "
            f"{', '.join(s.value for s in SlotId)}.") from exc


@workflow_bp.post("/api/workflow/sessions")
def create_workflow_session():
    """Starts (or re-attaches to) the structured intake for a workflow."""
    body = request.get_json(silent=True) or {}
    raw_workflow = body.get("workflow", WorkflowType.LOCAL_FILE_ROLL_FORWARD.value)
    try:
        workflow = WorkflowType(raw_workflow)
    except ValueError:
        return jsonify({"error": f"Unknown workflow '{raw_workflow}'."}), 400

    session_id = body.get("session_id")
    if not session_id:
        return jsonify({
            "error": "session_id is required — upload establishes the session via "
                     "POST /api/documents."
        }), 400

    existing = _load_session(session_id)
    if existing is not None and existing.workflow_type == workflow:
        return jsonify(existing.to_dict())

    session = WorkflowIntakeSession(
        session_id=session_id,
        workflow_type=workflow,
        target_fiscal_year=body.get("target_fiscal_year"),
    )
    _save_session(session)
    return jsonify(session.to_dict())


@workflow_bp.get("/api/workflow/<session_id>")
def get_workflow_session(session_id: str):
    session = _load_session(session_id)
    if session is None:
        return jsonify({"error": "No workflow intake has been started for this session."}), 404
    return jsonify(session.to_dict())


@workflow_bp.post("/api/workflow/<session_id>/slots/<slot_id>/assign")
def assign_document_to_slot(session_id: str, slot_id: str):
    """Gives an already-perceived document its workflow ROLE.

    Runs the deterministic content profile, validates it against the slot, then
    recalculates readiness. Never mutates the document.
    """
    body = request.get_json(silent=True) or {}
    doc_id = body.get("doc_id") or body.get("document_id")
    if not doc_id:
        return jsonify({"error": "doc_id is required."}), 400

    session = _load_session(session_id)
    if session is None:
        return jsonify({"error": "No workflow intake has been started for this session."}), 404

    user_id = _get_user_id()
    try:
        slot = _parse_slot(slot_id)
        with _resolve_document(session_id, doc_id, user_id) as (path, meta):
            assignment = session.assign_document(
                slot_id=slot,
                document_id=doc_id,
                path=path,
                filename=meta["filename"],
                perception_status=meta.get("status", "ready"),
                element_count=meta.get("element_count"),
                actor=user_id,
            )
    except WorkflowIntakeError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # profiling failure must not lose the session
        return jsonify({"error": f"Could not profile this document: {exc}"}), 422

    _save_session(session)
    return jsonify({"assignment": assignment.to_dict(), **session.to_dict()})


@workflow_bp.delete("/api/workflow/<session_id>/slots/<slot_id>/documents/<doc_id>")
def remove_document_from_slot(session_id: str, slot_id: str, doc_id: str):
    """Removes a document's role. The document itself stays in the session."""
    session = _load_session(session_id)
    if session is None:
        return jsonify({"error": "No workflow intake has been started for this session."}), 404

    try:
        slot = _parse_slot(slot_id)
    except WorkflowIntakeError as exc:
        return jsonify({"error": str(exc)}), 400

    if not session.remove_document(slot, doc_id):
        return jsonify({"error": f"Document '{doc_id}' is not assigned to {slot.value}."}), 404

    _save_session(session)
    return jsonify(session.to_dict())


@workflow_bp.post("/api/workflow/<session_id>/slots/<slot_id>/documents/<doc_id>/review")
def review_flagged_document(session_id: str, slot_id: str, doc_id: str):
    """Records the explicit human decision to keep a flagged file.

    This is the only way a file whose role could not be confirmed stays in a
    slot, and it is never silent: the decision is stored on the assignment and
    every domain that file supplies is reported as Human review, not Ready.
    """
    body = request.get_json(silent=True) or {}
    decision = (body.get("decision") or "keep_for_review").lower()
    if decision != "keep_for_review":
        return jsonify({
            "error": f"Unsupported decision '{decision}'. Replace the file, or keep it for "
                     f"manual review — there is no silent override."
        }), 400

    session = _load_session(session_id)
    if session is None:
        return jsonify({"error": "No workflow intake has been started for this session."}), 404

    try:
        slot = _parse_slot(slot_id)
        assignment = session.acknowledge_for_review(slot, doc_id, actor=_get_user_id())
    except WorkflowIntakeError as exc:
        return jsonify({"error": str(exc)}), 400

    _save_session(session)
    return jsonify({"assignment": assignment.to_dict(), **session.to_dict()})


@workflow_bp.get("/api/workflow/<session_id>/agent-context")
def get_agent_context(session_id: str):
    """The structured workflow context the Agent consumes.

    Document ids carry the roles, so the Agent never infers the workflow — or
    which file is the template — from a filename.
    """
    session = _load_session(session_id)
    if session is None:
        return jsonify({"error": "No workflow intake has been started for this session."}), 404
    return jsonify(session.agent_workflow_context())

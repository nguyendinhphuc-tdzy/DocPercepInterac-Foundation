"""POST /api/gpts/map — GTPS-specific mapping execution.

Architecture boundary: this is the ONLY file under api/ that imports from
applications.gpts.*. It resolves already-perceived documents (via the
session manifest api/routes/documents.py maintains) into file paths and
hands them to applications/gpts/mapping_service.py, completely unchanged.

Role assignment (which doc_ids are "source" vs "target") is supplied
explicitly by the caller in the request body — this route never infers
roles, and api/routes/documents.py never assigns them. This is the "an
application explicitly declares a workflow" seam: uploading/perceiving
documents (documents.py) never implies this route gets called, and this
route never runs implicitly — it only runs when a caller deliberately
invokes it with explicit source/target doc_ids.
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.routes import documents as documents_module  # noqa: E402
from applications.gpts.mapping_service import run_mapping  # noqa: E402

gpts_bp = Blueprint("gpts", __name__)


def _element_to_dict(element) -> dict:
    return element.model_dump(mode="json")


@gpts_bp.post("/api/gpts/map")
def run_gpts_mapping():
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    source_doc_ids = body.get("source_doc_ids") or []
    target_doc_id = body.get("target_doc_id")

    if not session_id:
        return jsonify({"error": "'session_id' is required"}), 400
    if not source_doc_ids:
        return jsonify({"error": "'source_doc_ids' must be a non-empty list"}), 400
    if not target_doc_id:
        return jsonify({"error": "'target_doc_id' is required"}), 400

    session_dir = documents_module.UPLOAD_ROOT / secure_filename(session_id)
    if not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404

    manifest = documents_module._load_manifest(session_dir)
    documents = manifest["documents"]

    missing = [d for d in [*source_doc_ids, target_doc_id] if d not in documents]
    if missing:
        return jsonify({"error": f"Unknown doc_id(s): {missing}"}), 404

    # Deliberately the pristine uploaded files (not _current_path_for's
    # patched-aware resolution) — matches applications/gpts/mapping_service.py's
    # own "Clone & Replace" design: it always writes a fresh
    # <target>_patched.docx from the original target, never layers onto an
    # already-patched file. Using an already-patched target here would
    # produce a stale/incorrectly-named double-patched file.
    source_paths = [
        str(session_dir / documents[d]["stored_filename"]) for d in source_doc_ids
    ]
    target_path = str(session_dir / documents[target_doc_id]["stored_filename"])

    try:
        result = run_mapping(source_paths, target_path, str(session_dir))
    except Exception as exc:
        return jsonify({"error": f"Failed to run GTPS mapping: {exc}"}), 422

    # Reuses the generic download route — run_mapping writes
    # <target>_patched.docx using the same naming convention
    # api/routes/documents.py's download endpoint already looks for.
    download_url = (
        f"/api/documents/{session_id}/download/{target_doc_id}"
        if result.patched_docx_path
        else None
    )

    return jsonify({
        "session_id": session_id,
        "source_elements": [_element_to_dict(e) for e in result.source_elements],
        "target_elements": [_element_to_dict(e) for e in result.target_elements],
        "mapped": [asdict(m) for m in result.mapped],
        "download_url": download_url,
    })

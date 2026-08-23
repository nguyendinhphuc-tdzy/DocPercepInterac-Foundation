"""
POST /api/gpts/map — GTPS-specific mapping execution (Phase DEPLOY-1).
======================================================================
Location: foundation/api/routes/gpts.py

Architecture boundary: this is the ONLY file under api/ that imports from
applications.gpts.*. Resolves documents using DocumentStorage and DocumentRepository
with guaranteed temporary file cleanup.
"""
from __future__ import annotations

import contextlib
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.gpts.mapping_service import run_mapping  # noqa: E402
from adapters.storage import get_storage  # noqa: E402
from adapters.repository import DocumentVersionRecord, get_repositories  # noqa: E402

gpts_bp = Blueprint("gpts", __name__)


def _get_user_id() -> str:
    return request.headers.get("X-User-Id", "anonymous")


def _element_to_dict(element) -> dict:
    return element.model_dump(mode="json")


@gpts_bp.post("/api/gpts/map")
def run_gpts_mapping():
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    source_doc_ids = body.get("source_doc_ids") or []
    target_doc_id = body.get("target_doc_id")
    user_id = _get_user_id()

    if not session_id:
        return jsonify({"error": "'session_id' is required"}), 400
    if not source_doc_ids:
        return jsonify({"error": "'source_doc_ids' must be a non-empty list"}), 400
    if not target_doc_id:
        return jsonify({"error": "'target_doc_id' is required"}), 400

    storage = get_storage()
    repos = get_repositories()

    target_doc = repos.documents.get_document(session_id, target_doc_id, user_id=user_id)
    if not target_doc:
        # Fallback to local session_dir inspection for legacy tests
        upload_root = Path(__file__).resolve().parents[2] / ".uploads"
        session_dir = upload_root / secure_filename(session_id)
        if not session_dir.is_dir():
            return jsonify({"error": "Unknown session_id"}), 404

    # Acquire all source and target document paths inside exit stack for guaranteed cleanup
    with contextlib.ExitStack() as stack:
        source_paths = []
        for s_id in source_doc_ids:
            try:
                s_path = stack.enter_context(
                    storage.get_document_path(session_id, s_id, is_patched=False, user_id=user_id)
                )
                source_paths.append(str(s_path))
            except Exception:
                return jsonify({"error": f"Unknown source doc_id '{s_id}'"}), 404

        try:
            t_path = stack.enter_context(
                storage.get_document_path(session_id, target_doc_id, is_patched=False, user_id=user_id)
            )
        except Exception:
            return jsonify({"error": f"Unknown target doc_id '{target_doc_id}'"}), 404

        # Run mapping output to a temporary working directory
        temp_work_dir = tempfile.TemporaryDirectory()
        stack.enter_context(temp_work_dir)

        try:
            result = run_mapping(source_paths, str(t_path), temp_work_dir.name)
        except Exception as exc:
            return jsonify({"error": f"Failed to run GTPS mapping: {exc}"}), 422

        # If a patched file was written, persist it to storage
        download_url = None
        if result.patched_docx_path and Path(result.patched_docx_path).exists():
            patched_bytes = Path(result.patched_docx_path).read_bytes()
            filename = target_doc.original_filename if target_doc else Path(t_path).name
            storage_res = storage.save_document(
                session_id=session_id,
                doc_id=target_doc_id,
                filename=filename,
                data=patched_bytes,
                is_patched=True,
                user_id=user_id,
            )

            # Record version
            latest = repos.documents.get_latest_version(session_id, target_doc_id, user_id=user_id)
            next_ver = (latest.version_number + 1) if latest else 2
            repos.documents.create_version(
                DocumentVersionRecord(
                    version_id=str(tempfile.NamedTemporaryFile().name),
                    doc_id=target_doc_id,
                    session_id=session_id,
                    user_id=user_id,
                    version_number=next_ver,
                    sha256=storage_res.file_hash,
                    storage_path=storage_res.storage_path,
                    is_patched=True,
                    size_bytes=storage_res.size_bytes,
                )
            )
            download_url = f"/api/documents/{session_id}/download/{target_doc_id}"

    return jsonify({
        "session_id": session_id,
        "source_elements": [_element_to_dict(e) for e in result.source_elements],
        "target_elements": [_element_to_dict(e) for e in result.target_elements],
        "mapped": [asdict(m) for m in result.mapped],
        "download_url": download_url,
    })

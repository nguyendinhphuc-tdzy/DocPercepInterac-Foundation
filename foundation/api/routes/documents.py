"""
POST /api/documents, GET /api/documents/<session_id>,
GET /api/documents/<session_id>/elements/<doc_id>,
PATCH /api/documents/<session_id>/elements/<doc_id>,
GET /api/documents/<session_id>/download/<doc_id> — the generic,
use-case-agnostic document layer: Perceive (extract + assign anchors +
classify) and Anchor-based read/write, nothing else.

Updated for Phase DEPLOY-1:
- Uses DocumentStorage abstraction (Local or Supabase Object Storage).
- Uses DocumentRepository for session and version metadata with user isolation.
- Guarantees ephemeral temp-file cleanup on all processing paths.
- Preserves full backward-compatibility with local manifest.json files and tests.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Annotated, Any, Optional

from flask import Blueprint, Response, jsonify, request, send_file
from pydantic import Field, TypeAdapter, ValidationError
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from perception.anchor_builder import assign_anchors  # noqa: E402
from perception.element_classifier import classify_blocks  # noqa: E402
from perception.models import Anchor  # noqa: E402
from perception.parser import extract_geometry, extract_media_manifest, resolve_media_bytes  # noqa: E402
from output.writeback import WritebackEngine  # noqa: E402
from output.lineage import LineageLogger  # noqa: E402
from adapters.storage import get_storage  # noqa: E402
from adapters.repository import (  # noqa: E402
    DocumentRecord,
    DocumentVersionRecord,
    LineageEventRecord,
    get_repositories,
)

documents_bp = Blueprint("documents", __name__)

_ANCHOR_ADAPTER = TypeAdapter(Annotated[Anchor, Field(discriminator="format")])

# Preserved for backward-compatibility in legacy test monkeypatching
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"

SUPPORTED_FORMATS = {"docx", "xlsx", "pdf"}


def _get_user_id() -> str:
    """Extracts user_id from Authorization / X-User-Id header or defaults to anonymous."""
    return request.headers.get("X-User-Id", "anonymous")


def _element_to_dict(element) -> dict:
    return element.model_dump(mode="json")


def _perceive_file(path: str, fmt: str) -> list:
    """The generic "See" pipeline: extract -> assign anchors -> classify."""
    blocks = extract_geometry(path)
    anchors = assign_anchors(blocks, fmt)
    return classify_blocks(blocks, fmt, anchors)


def _manifest_path(session_dir: Path) -> Path:
    return session_dir / "manifest.json"


def _load_manifest(session_dir: Path) -> dict:
    path = _manifest_path(session_dir)
    if not path.exists():
        return {"documents": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"documents": {}}


def _save_manifest(session_dir: Path, manifest: dict) -> None:
    try:
        session_dir.mkdir(parents=True, exist_ok=True)
        _manifest_path(session_dir).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception:
        pass


def _current_path_for(session_dir: Path, entry: dict) -> Path:
    stored_path = session_dir / entry["stored_filename"]
    patched = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
    return patched if patched.exists() else stored_path


def _doc_summary(doc: DocumentRecord) -> dict:
    return {
        "doc_id": doc.doc_id,
        "filename": doc.original_filename,
        "format": doc.format,
        "status": doc.status,
        "element_count": doc.element_count,
        "error": doc.error,
    }


@documents_bp.post("/api/documents")
def upload_document():
    """Upload ONE document, persist it via storage abstraction, and perceive it synchronously."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Missing 'file'"}), 400

    fmt = Path(file.filename).suffix.lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        return jsonify({
            "error": f"Unsupported format '.{fmt}' — supported: {sorted(SUPPORTED_FORMATS)}"
        }), 400

    session_id = request.form.get("session_id") or str(uuid.uuid4())
    user_id = _get_user_id()
    doc_id = str(uuid.uuid4())

    storage = get_storage()
    repos = get_repositories()

    # Ensure session exists
    repos.sessions.get_or_create(session_id, user_id=user_id)

    # Read binary bytes
    file_bytes = file.read()

    # Save to storage abstraction
    storage_res = storage.save_document(
        session_id=session_id,
        doc_id=doc_id,
        filename=file.filename,
        data=file_bytes,
        is_patched=False,
        user_id=user_id,
    )

    doc_record = DocumentRecord(
        doc_id=doc_id,
        session_id=session_id,
        user_id=user_id,
        original_filename=file.filename,
        format=fmt,
        status="ready",
        element_count=0,
        error=None,
    )

    # Also maintain local session dir & manifest.json for local/test compatibility
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{doc_id}_{secure_filename(file.filename)}"
    stored_path = session_dir / stored_filename
    if not stored_path.exists():
        stored_path.write_bytes(file_bytes)

    # Perceive document inside safe temp context manager (guaranteed cleanup in finally)
    try:
        with storage.get_document_path(session_id, doc_id, is_patched=False, user_id=user_id) as doc_path:
            elements = _perceive_file(str(doc_path), fmt)
            doc_record.element_count = len(elements)
    except Exception as exc:
        doc_record.status = "error"
        doc_record.error = str(exc)

    # Persist document metadata and initial version
    repos.documents.save_document(doc_record)
    repos.documents.create_version(
        DocumentVersionRecord(
            version_id=str(uuid.uuid4()),
            doc_id=doc_id,
            session_id=session_id,
            user_id=user_id,
            version_number=1,
            sha256=storage_res.file_hash,
            storage_path=storage_res.storage_path,
            is_patched=False,
            element_count=doc_record.element_count,
            size_bytes=storage_res.size_bytes,
        )
    )

    # Sync local manifest
    manifest = _load_manifest(session_dir)
    manifest["documents"][doc_id] = {
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "format": fmt,
        "status": doc_record.status,
        "element_count": doc_record.element_count,
        "error": doc_record.error,
    }
    _save_manifest(session_dir, manifest)

    return jsonify({"session_id": session_id, **_doc_summary(doc_record)})


@documents_bp.get("/api/documents/<session_id>")
def list_documents(session_id: str):
    user_id = _get_user_id()
    repos = get_repositories()

    docs = repos.documents.list_documents(session_id, user_id=user_id)
    if docs:
        return jsonify({
            "session_id": session_id,
            "documents": [_doc_summary(d) for d in docs],
        })

    # Fallback to local manifest if repository has no records (e.g. test seeding)
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    if session_dir.is_dir():
        manifest = _load_manifest(session_dir)
        documents = [
            {
                "doc_id": d_id,
                "filename": entry.get("original_filename", ""),
                "format": entry.get("format", ""),
                "status": entry.get("status", "ready"),
                "element_count": entry.get("element_count", 0),
                "error": entry.get("error"),
            }
            for d_id, entry in manifest.get("documents", {}).items()
        ]
        return jsonify({"session_id": session_id, "documents": documents})

    return jsonify({"error": "Unknown session_id"}), 404


@documents_bp.get("/api/documents/<session_id>/elements/<doc_id>")
def get_document_elements(session_id: str, doc_id: str):
    """Elements are fetched on demand per document and re-extracted deterministically."""
    user_id = _get_user_id()
    storage = get_storage()
    repos = get_repositories()

    doc = repos.documents.get_document(session_id, doc_id, user_id=user_id)
    session_dir = UPLOAD_ROOT / secure_filename(session_id)

    if doc is None and session_dir.is_dir():
        # Fallback to local manifest
        manifest = _load_manifest(session_dir)
        entry = manifest.get("documents", {}).get(doc_id)
        if entry:
            doc = DocumentRecord(
                doc_id=doc_id,
                session_id=session_id,
                user_id=user_id,
                original_filename=entry["original_filename"],
                format=entry["format"],
                status=entry.get("status", "ready"),
                element_count=entry.get("element_count", 0),
                error=entry.get("error"),
            )

    if doc is None:
        return jsonify({"error": "Unknown doc_id"}), 404
    if doc.status != "ready":
        return jsonify({"error": f"Document is not ready (status={doc.status})"}), 409

    # Check if local session dir has the file or if storage does
    if session_dir.is_dir():
        manifest = _load_manifest(session_dir)
        entry = manifest.get("documents", {}).get(doc_id)
        if entry:
            local_path = _current_path_for(session_dir, entry)
            if local_path.exists():
                elements = _perceive_file(str(local_path), doc.format)
                media = extract_media_manifest(str(local_path), doc.format)
                return jsonify({
                    "doc_id": doc_id,
                    "elements": [_element_to_dict(e) for e in elements],
                    "media": [m.model_dump(mode="json") for m in media],
                })

    is_patched = storage.document_exists(session_id, doc_id, is_patched=True, user_id=user_id)
    with storage.get_document_path(session_id, doc_id, is_patched=is_patched, user_id=user_id) as doc_path:
        elements = _perceive_file(str(doc_path), doc.format)
        media = extract_media_manifest(str(doc_path), doc.format)

    return jsonify({
        "doc_id": doc_id,
        "elements": [_element_to_dict(e) for e in elements],
        "media": [m.model_dump(mode="json") for m in media],
    })


@documents_bp.patch("/api/documents/<session_id>/elements/<doc_id>")
def patch_document_element(session_id: str, doc_id: str):
    """Live-edit endpoint: applies patch to document, stores patched version, records lineage."""
    user_id = _get_user_id()
    storage = get_storage()
    repos = get_repositories()

    doc = repos.documents.get_document(session_id, doc_id, user_id=user_id)
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    manifest_entry = None

    if session_dir.is_dir():
        manifest = _load_manifest(session_dir)
        manifest_entry = manifest.get("documents", {}).get(doc_id)

    if doc is None and manifest_entry:
        doc = DocumentRecord(
            doc_id=doc_id,
            session_id=session_id,
            user_id=user_id,
            original_filename=manifest_entry["original_filename"],
            format=manifest_entry["format"],
            status=manifest_entry.get("status", "ready"),
        )

    if doc is None and not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404
    if doc is None:
        return jsonify({"error": "Unknown doc_id"}), 404

    body = request.get_json(silent=True) or {}
    anchor_dict = body.get("anchor")
    new_value = body.get("value")
    if anchor_dict is None or new_value is None:
        return jsonify({"error": "Body must include 'anchor' and 'value'"}), 400

    try:
        anchor = _ANCHOR_ADAPTER.validate_python(anchor_dict)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid anchor: {exc}"}), 400

    # Local fallback for direct disk edits
    if session_dir.is_dir() and manifest_entry:
        working_path = _current_path_for(session_dir, manifest_entry)
        stored_stem = Path(manifest_entry["stored_filename"]).stem
        stored_suffix = Path(manifest_entry["stored_filename"]).suffix
        output_path = session_dir / f"{stored_stem}_patched{stored_suffix}"

        try:
            message = WritebackEngine().apply_single_patch(
                str(working_path), anchor, new_value, str(output_path)
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422

        LineageLogger(log_dir=str(session_dir / ".lineage_logs")).log_mapping(
            target_anchor=anchor.model_dump_json(),
            target_value=new_value,
            source_file="manual edit (UI)",
            source_anchor="user",
            confidence=1.0,
        )

        return jsonify({
            "status": "ok",
            "message": message,
            "download_url": f"/api/documents/{session_id}/download/{doc_id}",
        })

    is_already_patched = storage.document_exists(session_id, doc_id, is_patched=True, user_id=user_id)

    # Apply patch within safe tempfile lifecycle
    with storage.get_document_path(session_id, doc_id, is_patched=is_already_patched, user_id=user_id) as current_path:
        temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=current_path.suffix)
        temp_out_path = Path(temp_out.name)
        temp_out.close()

        try:
            message = WritebackEngine().apply_single_patch(
                str(current_path), anchor, new_value, str(temp_out_path)
            )
            patched_bytes = temp_out_path.read_bytes()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 422
        finally:
            if temp_out_path.exists():
                try:
                    temp_out_path.unlink()
                except OSError:
                    pass

    # Save patched version to storage
    storage_res = storage.save_document(
        session_id=session_id,
        doc_id=doc_id,
        filename=doc.original_filename,
        data=patched_bytes,
        is_patched=True,
        user_id=user_id,
    )

    # Record version
    latest = repos.documents.get_latest_version(session_id, doc_id, user_id=user_id)
    next_ver = (latest.version_number + 1) if latest else 2
    repos.documents.create_version(
        DocumentVersionRecord(
            version_id=str(uuid.uuid4()),
            doc_id=doc_id,
            session_id=session_id,
            user_id=user_id,
            version_number=next_ver,
            sha256=storage_res.file_hash,
            storage_path=storage_res.storage_path,
            is_patched=True,
            size_bytes=storage_res.size_bytes,
        )
    )

    # Log Lineage
    repos.lineage.log_mapping(
        LineageEventRecord(
            session_id=session_id,
            user_id=user_id,
            target_anchor=anchor.model_dump_json(),
            target_value_hash=storage_res.file_hash,
            source_file="manual edit (UI)",
            source_anchor="user",
            confidence=1.0,
        )
    )

    return jsonify({
        "status": "ok",
        "message": message,
        "download_url": f"/api/documents/{session_id}/download/{doc_id}",
    })


@documents_bp.get("/api/documents/<session_id>/download/<doc_id>")
def download_document(session_id: str, doc_id: str):
    """Serves the document's current file (patched if exists, else pristine upload)."""
    user_id = _get_user_id()
    storage = get_storage()
    repos = get_repositories()

    doc = repos.documents.get_document(session_id, doc_id, user_id=user_id)
    session_dir = UPLOAD_ROOT / secure_filename(session_id)

    if session_dir.is_dir():
        manifest = _load_manifest(session_dir)
        entry = manifest.get("documents", {}).get(doc_id)
        if entry:
            current_path = _current_path_for(session_dir, entry)
            if current_path.exists():
                return send_file(current_path, as_attachment=True, download_name=current_path.name)

    if doc is None:
        return jsonify({"error": "Unknown doc_id"}), 404

    is_patched = storage.document_exists(session_id, doc_id, is_patched=True, user_id=user_id)
    try:
        data = storage.get_document_bytes(session_id, doc_id, is_patched=is_patched, user_id=user_id)
    except Exception:
        return jsonify({"error": "No file available for this document"}), 404

    filename = doc.original_filename
    if is_patched:
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        filename = f"{stem}_patched{suffix}"

    return send_file(
        io.BytesIO(data),
        as_attachment=True,
        download_name=filename,
        mimetype="application/octet-stream",
    )


@documents_bp.get("/api/documents/<session_id>/media/<doc_id>/<media_id>")
def get_document_media(session_id: str, doc_id: str, media_id: str):
    """Serves embedded media bytes with guaranteed temp file cleanup."""
    user_id = _get_user_id()
    storage = get_storage()
    repos = get_repositories()

    doc = repos.documents.get_document(session_id, doc_id, user_id=user_id)
    session_dir = UPLOAD_ROOT / secure_filename(session_id)

    if session_dir.is_dir():
        manifest = _load_manifest(session_dir)
        entry = manifest.get("documents", {}).get(doc_id)
        if entry:
            local_path = _current_path_for(session_dir, entry)
            if local_path.exists():
                resolved = resolve_media_bytes(str(local_path), entry["format"], media_id)
                if resolved is None:
                    return jsonify({"error": "Unknown or unresolvable media_id"}), 404
                data, mime_type = resolved
                return Response(data, mimetype=mime_type)

    if doc is None:
        return jsonify({"error": "Unknown doc_id"}), 404

    is_patched = storage.document_exists(session_id, doc_id, is_patched=True, user_id=user_id)
    with storage.get_document_path(session_id, doc_id, is_patched=is_patched, user_id=user_id) as doc_path:
        resolved = resolve_media_bytes(str(doc_path), doc.format, media_id)

    if resolved is None:
        return jsonify({"error": "Unknown or unresolvable media_id"}), 404

    data, mime_type = resolved
    return Response(data, mimetype=mime_type)

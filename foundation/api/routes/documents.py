"""POST /api/documents, GET /api/documents/<session_id>,
GET /api/documents/<session_id>/elements/<doc_id>,
PATCH /api/documents/<session_id>/elements/<doc_id>,
GET /api/documents/<session_id>/download/<doc_id> — the generic,
use-case-agnostic document layer: Perceive (extract + assign anchors +
classify) and Anchor-based read/write, nothing else.

Architecture boundary: this module imports ONLY from perception.* and
output.* (+ Flask/pydantic/werkzeug/stdlib) — NEVER from applications.*.
Uploading and perceiving a document establishes document context only; it
never infers or assigns a role (no "source"/"target"), never runs a
mapping, and the response never contains GTPS-shaped fields (mapped,
source_elements, target_elements, ...). Role assignment + any application
workflow (e.g. GTPS mapping) lives entirely in api/routes/gpts.py, which
is the only place under api/ allowed to import applications.gpts.*.

Session/document model:
  - A "session" (`session_id`) is just a directory under `.uploads/` that
    accumulates independently-uploaded documents plus a small
    `manifest.json` recording their stable `doc_id` -> metadata. The first
    upload with no `session_id` creates one; subsequent uploads pass it
    back to add more documents to the same session.
  - A "document" (`doc_id`, a fresh uuid4 minted at upload time — never a
    filename, array index, or upload-order position) is perceived
    synchronously on upload and gets an explicit per-document status
    ("ready" or "error"), independent of every other document in the
    session — there is no single workspace-wide processing flag.
  - No "task" exists here at all. A task (e.g. a GTPS mapping run) is only
    ever created by an explicit call to a route like POST /api/gpts/map.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any

from flask import Blueprint, jsonify, request, send_file
from pydantic import Field, TypeAdapter, ValidationError
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from perception.anchor_builder import assign_anchors  # noqa: E402
from perception.element_classifier import classify_blocks  # noqa: E402
from perception.models import Anchor  # noqa: E402
from perception.parser import extract_geometry  # noqa: E402
from output.lineage import LineageLogger  # noqa: E402
from output.writeback import WritebackEngine  # noqa: E402

documents_bp = Blueprint("documents", __name__)

_ANCHOR_ADAPTER = TypeAdapter(Annotated[Anchor, Field(discriminator="format")])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"

# Validated by extension only, same as perception.parser.extract_geometry's
# own dispatch — perception.detector.detect_format's MIME sniff (libmagic)
# misidentifies real .docx/.xlsx files as application/octet-stream on this
# dev machine (python-magic-bin database quirk on Windows), so it would
# reject legitimate uploads. Not this task's concern to fix.
SUPPORTED_FORMATS = {"docx", "xlsx", "pdf"}


def _element_to_dict(element) -> dict:
    return element.model_dump(mode="json")


def _perceive_file(path: str, fmt: str) -> list:
    """The generic "See" pipeline: extract -> assign anchors -> classify.
    No application ever needs to reimplement this — it's exactly the
    perception.element_classifier seam applications/gpts/mapping_service.py
    also uses."""
    blocks = extract_geometry(path)
    anchors = assign_anchors(blocks, fmt)
    return classify_blocks(blocks, fmt, anchors)


def _manifest_path(session_dir: Path) -> Path:
    return session_dir / "manifest.json"


def _load_manifest(session_dir: Path) -> dict:
    path = _manifest_path(session_dir)
    if not path.exists():
        return {"documents": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_manifest(session_dir: Path, manifest: dict) -> None:
    _manifest_path(session_dir).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _current_path_for(session_dir: Path, entry: dict) -> Path:
    """The document's current file on disk: the live-edited (`_patched`)
    version if one exists, otherwise the pristine upload."""
    stored_path = session_dir / entry["stored_filename"]
    patched = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
    return patched if patched.exists() else stored_path


def _doc_summary(doc_id: str, entry: dict) -> dict:
    return {
        "doc_id": doc_id,
        "filename": entry["original_filename"],
        "format": entry["format"],
        "status": entry["status"],
        "element_count": entry["element_count"],
        "error": entry["error"],
    }


@documents_bp.post("/api/documents")
def upload_document():
    """Upload ONE document and perceive it synchronously. One document per
    call (not a batch) so each document's status is genuinely independent
    of every other's — the caller can upload several documents concurrently
    and see each resolve to "ready"/"error" on its own, rather than a
    single workspace-wide flag that hides per-document failures."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Missing 'file'"}), 400

    fmt = Path(file.filename).suffix.lower().lstrip(".")
    if fmt not in SUPPORTED_FORMATS:
        return jsonify({
            "error": f"Unsupported format '.{fmt}' — supported: {sorted(SUPPORTED_FORMATS)}"
        }), 400

    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}_{secure_filename(file.filename)}"
    stored_path = session_dir / stored_filename
    file.save(stored_path)

    entry: dict[str, Any] = {
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "format": fmt,
        "status": "ready",
        "element_count": 0,
        "error": None,
    }
    try:
        elements = _perceive_file(str(stored_path), fmt)
        entry["element_count"] = len(elements)
    except Exception as exc:  # a parse failure is a per-document status, not a transport error
        entry["status"] = "error"
        entry["error"] = str(exc)

    manifest = _load_manifest(session_dir)
    manifest["documents"][doc_id] = entry
    _save_manifest(session_dir, manifest)

    return jsonify({"session_id": session_id, **_doc_summary(doc_id, entry)})


@documents_bp.get("/api/documents/<session_id>")
def list_documents(session_id: str):
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    if not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404

    manifest = _load_manifest(session_dir)
    documents = [_doc_summary(doc_id, entry) for doc_id, entry in manifest["documents"].items()]
    return jsonify({"session_id": session_id, "documents": documents})


@documents_bp.get("/api/documents/<session_id>/elements/<doc_id>")
def get_document_elements(session_id: str, doc_id: str):
    """Elements are fetched lazily, on demand, per document — not inlined
    into the upload response. Perception is deterministic, so this simply
    re-runs it against the document's current (possibly patched) file
    rather than caching a copy server-side."""
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    if not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404

    manifest = _load_manifest(session_dir)
    entry = manifest["documents"].get(doc_id)
    if entry is None:
        return jsonify({"error": "Unknown doc_id"}), 404
    if entry["status"] != "ready":
        return jsonify({"error": f"Document is not ready (status={entry['status']})"}), 409

    path = _current_path_for(session_dir, entry)
    elements = _perceive_file(str(path), entry["format"])
    return jsonify({"doc_id": doc_id, "elements": [_element_to_dict(e) for e in elements]})


@documents_bp.patch("/api/documents/<session_id>/elements/<doc_id>")
def patch_document_element(session_id: str, doc_id: str):
    """Live-edit endpoint: writes one new value directly into this specific
    document at the element's Anchor, without re-running any pipeline.
    Works for ANY perceived document of a writeable format (currently DOCX
    and XLSX — output/writeback.py's own, real technical limit; PDF is
    read-only there). Not restricted to a single privileged "target"
    document the way the old /api/process PATCH route was."""
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    if not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404

    manifest = _load_manifest(session_dir)
    entry = manifest["documents"].get(doc_id)
    if entry is None:
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

    working_path = _current_path_for(session_dir, entry)
    stored_stem = Path(entry["stored_filename"]).stem
    stored_suffix = Path(entry["stored_filename"]).suffix
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


@documents_bp.get("/api/documents/<session_id>/download/<doc_id>")
def download_document(session_id: str, doc_id: str):
    session_dir = UPLOAD_ROOT / secure_filename(session_id)
    if not session_dir.is_dir():
        return jsonify({"error": "Unknown session_id"}), 404

    manifest = _load_manifest(session_dir)
    entry = manifest["documents"].get(doc_id)
    if entry is None:
        return jsonify({"error": "Unknown doc_id"}), 404

    stored_path = session_dir / entry["stored_filename"]
    patched_path = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
    if not patched_path.exists():
        return jsonify({"error": "No patched output for this document"}), 404

    return send_file(patched_path, as_attachment=True, download_name=patched_path.name)

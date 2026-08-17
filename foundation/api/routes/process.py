"""POST /api/process, PATCH /api/elements/<process_id>,
GET /api/download/<process_id> — HTTP surface over
applications/gpts/mapping_service.py + output/writeback.py.
"""
from __future__ import annotations

import shutil
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

from flask import Blueprint, jsonify, request, send_file
from pydantic import Field, TypeAdapter, ValidationError
from werkzeug.utils import secure_filename

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.gpts.mapping_service import run_mapping  # noqa: E402
from output.lineage import LineageLogger  # noqa: E402
from output.writeback import WritebackEngine  # noqa: E402
from perception.models import Anchor  # noqa: E402

process_bp = Blueprint("process", __name__)

_ANCHOR_ADAPTER = TypeAdapter(Annotated[Anchor, Field(discriminator="format")])

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"

# Validated by extension only, same as perception.parser.extract_geometry's
# own dispatch — perception.detector.detect_format's MIME sniff (libmagic)
# misidentifies real .docx/.xlsx files as application/octet-stream on this
# dev machine (python-magic-bin database quirk on Windows), so it would
# reject legitimate uploads. Not this task's concern to fix.
SOURCE_FORMATS = {"xlsx", "pdf"}
TARGET_FORMATS = {"docx"}


def _element_to_dict(element) -> dict:
    return element.model_dump(mode="json")


@process_bp.post("/api/process")
def process_documents():
    # Any number of source files — one function's use case might need just
    # one (a single BCTC), another might need several (e.g. GTPS's Local
    # File mapping needs FA&RPTs + Appendix I together). The frontend
    # appends every selected file under the same "source" field name.
    source_files = [f for f in request.files.getlist("source") if f.filename]
    target_file = request.files.get("target")
    if not source_files:
        return jsonify({"error": "Missing 'source' file(s)"}), 400
    if target_file is None or not target_file.filename:
        return jsonify({"error": "Missing 'target' file"}), 400

    process_id = str(uuid.uuid4())
    process_dir = UPLOAD_ROOT / process_id
    process_dir.mkdir(parents=True, exist_ok=True)

    target_ext = Path(target_file.filename).suffix.lower().lstrip(".")
    if target_ext not in TARGET_FORMATS:
        return jsonify({
            "error": f"Target must be one of {sorted(TARGET_FORMATS)}, got '.{target_ext}'"
        }), 400

    source_paths = []
    for i, source_file in enumerate(source_files):
        source_ext = Path(source_file.filename).suffix.lower().lstrip(".")
        if source_ext not in SOURCE_FORMATS:
            return jsonify({
                "error": f"Source '{source_file.filename}' must be one of {sorted(SOURCE_FORMATS)}, got '.{source_ext}'"
            }), 400
        # Index-prefixed so two uploaded files that happen to share a name
        # never collide on disk.
        source_path = process_dir / f"{i}_{secure_filename(source_file.filename)}"
        source_file.save(source_path)
        source_paths.append(str(source_path))

    target_path = process_dir / secure_filename(target_file.filename)
    target_file.save(target_path)

    try:
        result = run_mapping(source_paths, str(target_path), str(process_dir))
    except Exception as exc:  # parsing failures surface as a clean 422, not a 500 stack trace
        return jsonify({"error": f"Failed to process documents: {exc}"}), 422

    download_url = f"/api/download/{process_id}" if result.patched_docx_path else None

    return jsonify({
        "process_id": process_id,
        "source_elements": [_element_to_dict(e) for e in result.source_elements],
        "target_elements": [_element_to_dict(e) for e in result.target_elements],
        "mapped": [asdict(m) for m in result.mapped],
        "download_url": download_url,
    })


@process_bp.patch("/api/elements/<process_id>")
def patch_element(process_id: str):
    """Live-edit endpoint for the workspace UI: writes one new value
    directly into the output document at the element's Anchor, without
    re-running the full pipeline. Body: {"anchor": {...}, "value": "..."}.

    Only DOCX output is wired up — that's the only format this demo
    actually produces as an editable "output" (source Excel is read-only
    input). Edits accumulate on the same patched file: the first edit
    seeds it from the pristine target (in case no DEMO_RULES mapping
    produced one yet), every edit after that builds on the previous one.
    """
    process_dir = UPLOAD_ROOT / secure_filename(process_id)
    if not process_dir.is_dir():
        return jsonify({"error": "Unknown process_id"}), 404

    body = request.get_json(silent=True) or {}
    anchor_dict = body.get("anchor")
    new_value = body.get("value")
    if anchor_dict is None or new_value is None:
        return jsonify({"error": "Body must include 'anchor' and 'value'"}), 400

    try:
        anchor = _ANCHOR_ADAPTER.validate_python(anchor_dict)
    except ValidationError as exc:
        return jsonify({"error": f"Invalid anchor: {exc}"}), 400

    if anchor.format != "docx":
        return jsonify({
            "error": f"Editing '{anchor.format}' output isn't supported yet — only the DOCX target/output is editable"
        }), 400

    patched_candidates = list(process_dir.glob("*_patched.docx"))
    if patched_candidates:
        working_path = patched_candidates[0]
    else:
        target_candidates = [
            p for p in process_dir.glob("*.docx") if not p.name.endswith("_patched.docx")
        ]
        if not target_candidates:
            return jsonify({"error": "No target document found for this process_id"}), 404
        working_path = target_candidates[0].with_name(f"{target_candidates[0].stem}_patched.docx")
        shutil.copyfile(target_candidates[0], working_path)

    try:
        message = WritebackEngine().apply_single_patch(str(working_path), anchor, new_value, str(working_path))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422

    # Same lineage trail as the DEMO_RULES auto-mapping in
    # applications/gpts/mapping_service.py::run_mapping — manual edits
    # (including undo, which is just another edit with the prior value)
    # get an audit record too, not shown in the UI yet but on disk for
    # when that becomes a feature.
    LineageLogger(log_dir=str(process_dir / ".lineage_logs")).log_mapping(
        target_anchor=anchor.model_dump_json(),
        target_value=new_value,
        source_file="manual edit (UI)",
        source_anchor="user",
        confidence=1.0,
    )

    return jsonify({
        "status": "ok",
        "message": message,
        "download_url": f"/api/download/{process_id}",
    })


@process_bp.get("/api/download/<process_id>")
def download_patched(process_id: str):
    process_dir = UPLOAD_ROOT / secure_filename(process_id)
    if not process_dir.is_dir():
        return jsonify({"error": "Unknown process_id"}), 404

    candidates = list(process_dir.glob("*_patched.docx"))
    if not candidates:
        return jsonify({"error": "No patched output for this process_id"}), 404

    return send_file(candidates[0], as_attachment=True, download_name=candidates[0].name)

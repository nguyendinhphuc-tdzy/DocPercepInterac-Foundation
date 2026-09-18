"""
Demo Bridge API for GTPS Local File Real-Document Interactive Demo.
===================================================================
Location: foundation/api/routes/demo.py

Architecture Boundaries (AGENTS.md & CURRENT_BASELINE.md):
- Strictly read-only simulation & proposal projection.
- NEVER mutates source or template DOCX/XLSX binaries.
- NEVER calls WritebackEngine or performs Replay.
- NEVER creates an ApprovedChangeSet (proposals carry NO mutation authority).
- Uses RollForwardPlanner.plan() and workflow_intake.py for deterministic mapping.
"""
from __future__ import annotations

import io
import json
import mimetypes
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, jsonify, request, send_file
from werkzeug.utils import secure_filename

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from adapters.storage import get_storage
from applications.rollforward.models import (
    ExecutionGate,
    RegionClassification,
    SourceBindingStatus,
)
from applications.rollforward.planner import (
    DocumentRef,
    PlannerInputs,
    RollForwardPlanner,
)
from applications.rollforward.workflow_intake import (
    FiscalPeriod,
    SlotId,
    WorkflowIntakeSession,
)
from perception.anchor_builder import assign_anchors
from perception.element_classifier import classify_blocks
from perception.parser import extract_geometry

demo_bp = Blueprint("demo", __name__)

DEMO_DATA_DIR = ROOT_DIR.parent / "anonymize client" / "Demo files" / "Demo files"
if not DEMO_DATA_DIR.exists():
    DEMO_DATA_DIR = ROOT_DIR / "anonymize client" / "Demo files" / "Demo files"

# In-memory store for demo session state (isolated from production repositories)
_DEMO_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _get_user_id() -> str:
    return request.headers.get("X-User-Id", "anonymous")


def _get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _DEMO_SESSIONS:
        _DEMO_SESSIONS[session_id] = {
            "session_id": session_id,
            "documents": {},  # doc_id -> doc_info
            "roles": {
                "TARGET_TEMPLATE": None,      # doc_id
                "HISTORICAL_REFERENCE": None, # doc_id
                "CURRENT_SOURCE": [],        # list[doc_id]
            },
            "analysis_result": None,
            "decisions": {},  # proposal_id -> decision
        }
    return _DEMO_SESSIONS[session_id]


def _detect_role_hint(filename: str, format: str) -> Optional[str]:
    """Provides a soft heuristic hint only. The user MUST confirm role assignment."""
    fn = filename.lower()
    if format == "docx":
        if "template" in fn:
            return "TARGET_TEMPLATE"
        if "2023" in fn or "fy23" in fn or "final-local file for fy2023" in fn:
            return "HISTORICAL_REFERENCE"
    elif format in ("xlsx", "xlsm"):
        if "fa&rpt" in fn or "appendix" in fn:
            return "CURRENT_SOURCE"
    return None


def _calculate_readiness(session: Dict[str, Any]) -> Dict[str, Any]:
    roles = session["roles"]
    docs = session["documents"]

    tmpl_id = roles.get("TARGET_TEMPLATE")
    hist_id = roles.get("HISTORICAL_REFERENCE")
    src_ids = roles.get("CURRENT_SOURCE", [])

    template_ready = bool(tmpl_id and tmpl_id in docs)
    historical_ready = bool(hist_id and hist_id in docs)
    current_source_ready = bool(src_ids and any(sid in docs for sid in src_ids))

    return {
        "template_ready": template_ready,
        "historical_ready": historical_ready,
        "current_source_ready": current_source_ready,
        "all_ready": template_ready and historical_ready and current_source_ready,
    }


# ============================================================================
# 1. WORKSPACE & FILE INTAKE
# ============================================================================

@demo_bp.route("/demo/gtps/workspace", methods=["POST"])
@demo_bp.route("/api/demo/gtps/workspace", methods=["POST"])
def register_workspace():
    """Receives uploaded files or loads local demo files, registers real bytes in storage."""
    user_id = _get_user_id()
    storage = get_storage()

    # Determine session_id
    if request.is_json:
        body = request.get_json(silent=True) or {}
        session_id = body.get("session_id") or str(uuid.uuid4())
        load_local_demo = bool(body.get("load_local_demo"))
    else:
        session_id = request.form.get("session_id") or str(uuid.uuid4())
        load_local_demo = request.form.get("load_local_demo") in ("true", "1")

    session = _get_session(session_id)

    # If load_local_demo requested, load the real representative files from disk
    if load_local_demo and DEMO_DATA_DIR.exists():
        local_files = [
            (
                DEMO_DATA_DIR / "Compare LF" / "Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx",
                "TARGET_TEMPLATE"
            ),
            (
                DEMO_DATA_DIR / "Compare LF" / "HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx",
                "HISTORICAL_REFERENCE"
            ),
            (
                DEMO_DATA_DIR / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx",
                "CURRENT_SOURCE"
            ),
            (
                DEMO_DATA_DIR / "FA&RPTS & Appendix I" / "Appendix I" / "HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx",
                "CURRENT_SOURCE"
            ),
        ]
        for p, role in local_files:
            if not p.exists():
                continue
            doc_id = f"demo-doc-{p.stem[:12]}-{uuid.uuid4().hex[:6]}"
            data = p.read_bytes()
            fmt = p.suffix.lower().lstrip(".")
            res = storage.save_document(
                session_id=session_id,
                doc_id=doc_id,
                filename=p.name,
                data=data,
                user_id=user_id,
            )
            session["documents"][doc_id] = {
                "doc_id": doc_id,
                "filename": p.name,
                "format": fmt,
                "size_bytes": len(data),
                "file_hash": res.file_hash,
                "detected_role": role,
                "assigned_role": role,
                "local_path": str(p),
            }
            if role == "TARGET_TEMPLATE":
                session["roles"]["TARGET_TEMPLATE"] = doc_id
            elif role == "HISTORICAL_REFERENCE":
                session["roles"]["HISTORICAL_REFERENCE"] = doc_id
            elif role == "CURRENT_SOURCE":
                if doc_id not in session["roles"]["CURRENT_SOURCE"]:
                    session["roles"]["CURRENT_SOURCE"].append(doc_id)

    # Process any multipart uploaded files
    if "files" in request.files:
        files = request.files.getlist("files")
        for f in files:
            if not f or not f.filename:
                continue
            filename = secure_filename(f.filename) or f.filename
            data = f.read()
            fmt = Path(filename).suffix.lower().lstrip(".")
            doc_id = f"up-{uuid.uuid4().hex[:10]}"
            res = storage.save_document(
                session_id=session_id,
                doc_id=doc_id,
                filename=filename,
                data=data,
                user_id=user_id,
            )
            role_hint = _detect_role_hint(filename, fmt)
            session["documents"][doc_id] = {
                "doc_id": doc_id,
                "filename": filename,
                "format": fmt,
                "size_bytes": len(data),
                "file_hash": res.file_hash,
                "detected_role": role_hint,
                "assigned_role": None,  # User must confirm role
            }

    docs_list = list(session["documents"].values())
    readiness = _calculate_readiness(session)

    return jsonify({
        "session_id": session_id,
        "documents": docs_list,
        "roles": session["roles"],
        "readiness": readiness,
    })


@demo_bp.route("/demo/gtps/workspace/assign-role", methods=["POST"])
@demo_bp.route("/api/demo/gtps/workspace/assign-role", methods=["POST"])
def assign_role():
    """Assigns or reassigns a document's workflow role."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    doc_id = body.get("doc_id")
    role = body.get("role")  # TARGET_TEMPLATE, HISTORICAL_REFERENCE, CURRENT_SOURCE, or None

    if not session_id or session_id not in _DEMO_SESSIONS:
        return jsonify({"error": "Unknown session_id"}), 404
    session = _DEMO_SESSIONS[session_id]

    if not doc_id or doc_id not in session["documents"]:
        return jsonify({"error": "Unknown doc_id"}), 404

    # Remove doc_id from existing roles
    if session["roles"]["TARGET_TEMPLATE"] == doc_id:
        session["roles"]["TARGET_TEMPLATE"] = None
    if session["roles"]["HISTORICAL_REFERENCE"] == doc_id:
        session["roles"]["HISTORICAL_REFERENCE"] = None
    if doc_id in session["roles"]["CURRENT_SOURCE"]:
        session["roles"]["CURRENT_SOURCE"].remove(doc_id)

    # Assign new role if provided
    if role == "TARGET_TEMPLATE":
        # If another doc had TARGET_TEMPLATE, clear it
        old_t = session["roles"]["TARGET_TEMPLATE"]
        if old_t and old_t in session["documents"]:
            session["documents"][old_t]["assigned_role"] = None
        session["roles"]["TARGET_TEMPLATE"] = doc_id
        session["documents"][doc_id]["assigned_role"] = "TARGET_TEMPLATE"
    elif role == "HISTORICAL_REFERENCE":
        old_h = session["roles"]["HISTORICAL_REFERENCE"]
        if old_h and old_h in session["documents"]:
            session["documents"][old_h]["assigned_role"] = None
        session["roles"]["HISTORICAL_REFERENCE"] = doc_id
        session["documents"][doc_id]["assigned_role"] = "HISTORICAL_REFERENCE"
    elif role == "CURRENT_SOURCE":
        session["roles"]["CURRENT_SOURCE"].append(doc_id)
        session["documents"][doc_id]["assigned_role"] = "CURRENT_SOURCE"
    else:
        session["documents"][doc_id]["assigned_role"] = None

    # Reset prior analysis if inputs change
    session["analysis_result"] = None

    readiness = _calculate_readiness(session)
    return jsonify({
        "session_id": session_id,
        "documents": list(session["documents"].values()),
        "roles": session["roles"],
        "readiness": readiness,
    })


@demo_bp.route("/demo/gtps/workspace/remove-doc", methods=["POST"])
@demo_bp.route("/api/demo/gtps/workspace/remove-doc", methods=["POST"])
def remove_document():
    """Removes a document from the demo workspace."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    doc_id = body.get("doc_id")

    if not session_id or session_id not in _DEMO_SESSIONS:
        return jsonify({"error": "Unknown session_id"}), 404
    session = _DEMO_SESSIONS[session_id]

    if doc_id in session["documents"]:
        del session["documents"][doc_id]

    if session["roles"]["TARGET_TEMPLATE"] == doc_id:
        session["roles"]["TARGET_TEMPLATE"] = None
    if session["roles"]["HISTORICAL_REFERENCE"] == doc_id:
        session["roles"]["HISTORICAL_REFERENCE"] = None
    if doc_id in session["roles"]["CURRENT_SOURCE"]:
        session["roles"]["CURRENT_SOURCE"].remove(doc_id)

    session["analysis_result"] = None
    readiness = _calculate_readiness(session)

    return jsonify({
        "session_id": session_id,
        "documents": list(session["documents"].values()),
        "roles": session["roles"],
        "readiness": readiness,
    })


# ============================================================================
# 2. ANALYSIS & MAPPING EXECUTION (READ-ONLY)
# ============================================================================

@demo_bp.route("/demo/gtps/analyze", methods=["POST"])
@demo_bp.route("/api/demo/gtps/analyze", methods=["POST"])
def analyze_mapping():
    """Executes RollForwardPlanner.plan() on the assigned real documents.

    Strictly read-only: builds visual review proposals without mutating any DOCX.
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    if not session_id or session_id not in _DEMO_SESSIONS:
        return jsonify({"error": "Unknown session_id"}), 404

    session = _DEMO_SESSIONS[session_id]
    readiness = _calculate_readiness(session)
    if not readiness["all_ready"]:
        return jsonify({
            "error": "Cannot prepare draft: required document roles are not complete.",
            "readiness": readiness,
        }), 400

    storage = get_storage()
    user_id = _get_user_id()

    tmpl_id = session["roles"]["TARGET_TEMPLATE"]
    hist_id = session["roles"]["HISTORICAL_REFERENCE"]
    src_ids = session["roles"]["CURRENT_SOURCE"]

    tmpl_doc = session["documents"][tmpl_id]
    hist_doc = session["documents"][hist_id]
    src_docs = [session["documents"][sid] for sid in src_ids]

    import contextlib

    with contextlib.ExitStack() as stack:
        # Acquire actual paths to verify binaries
        tmpl_path = stack.enter_context(
            storage.get_document_path(session_id, tmpl_id, user_id=user_id)
        )
        hist_path = stack.enter_context(
            storage.get_document_path(session_id, hist_id, user_id=user_id)
        )
        source_paths = []
        for s_doc in src_docs:
            p = stack.enter_context(
                storage.get_document_path(session_id, s_doc["doc_id"], user_id=user_id)
            )
            source_paths.append((s_doc["doc_id"], p, s_doc["filename"]))

        # Profile documents and periods via workflow_intake
        hist_profile = WorkflowIntakeSession.profile_document(hist_path, SlotId.HISTORICAL_LOCAL_FILE)
        hist_year = hist_profile.signals.fiscal_year if hist_profile.signals else None

        source_years = []
        for _, sp, _ in source_paths:
            if sp.suffix.lower() in (".xlsx", ".xlsm"):
                sprof = WorkflowIntakeSession.profile_document(sp, SlotId.CURRENT_YEAR_SOURCES)
                if sprof.signals and sprof.signals.fiscal_year:
                    source_years.append(sprof.signals.fiscal_year)

        curr_year = max(source_years) if source_years else None
        hist_period = FiscalPeriod.of(hist_year) if hist_year else FiscalPeriod.of(2023)
        curr_period = FiscalPeriod.of(curr_year) if curr_year else FiscalPeriod.of(2024)

        planner_inputs = PlannerInputs(
            workflow_id=f"demo-{session_id}",
            session_id=session_id,
            historical=DocumentRef(hist_id, hist_path, hist_doc["filename"]),
            template=DocumentRef(tmpl_id, tmpl_path, tmpl_doc["filename"]),
            current_sources=tuple(
                DocumentRef(sid, sp, fn) for sid, sp, fn in source_paths
            ),
            historical_period=hist_period,
            current_period=curr_period,
        )

        try:
            plan_result = RollForwardPlanner.plan(planner_inputs)
        except Exception as exc:
            return jsonify({"error": f"RollForward planning failed: {exc}"}), 422

        # Transform planning results into rich review proposals for the UI
        proposals: List[Dict[str, Any]] = []

        for idx, outcome in enumerate(plan_result.outcomes):
            region = next((r for r in plan_result.manifest.regions if r.region_id == outcome.region_id), None)
            table_spec = next((t for t in plan_result.mutation_plan.table_mutations if t.target_region_id == outcome.region_id), None)
            diff = next((d for d in plan_result.diffs if d.region_id == outcome.region_id), None)

            # Map disposition to Section 9 states:
            # MAPPED ("Đã ánh xạ")
            # NEEDS_CONFIRMATION ("Cần xác nhận")
            # MISSING_SOURCE ("Thiếu dữ liệu")
            # UNSUPPORTED ("Chưa hỗ trợ")
            if outcome.disposition == "READY" and table_spec is not None:
                status = "MAPPED"
                status_label_vi = "Đã ánh xạ"
                status_label_en = "Mapped"
            elif outcome.disposition == "HUMAN_REVIEW":
                status = "NEEDS_CONFIRMATION"
                status_label_vi = "Cần xác nhận"
                status_label_en = "Needs confirmation"
            elif outcome.disposition == "BLOCKED":
                status = "MISSING_SOURCE"
                status_label_vi = "Thiếu dữ liệu"
                status_label_en = "Missing source"
            else:
                status = "UNSUPPORTED"
                status_label_vi = "Chưa hỗ trợ"
                status_label_en = "Unsupported"

            first_binding = region.current_sources[0] if (region and region.current_sources) else None
            src_evidence = None
            if first_binding and first_binding.status != SourceBindingStatus.MISSING:
                src_evidence = {
                    "source_doc_name": first_binding.source_doc_name,
                    "sheet_name": first_binding.sheet_name,
                    "cell_range": first_binding.cell_range,
                    "record_count": first_binding.provenance.get("record_count") if first_binding.provenance else None,
                    "matched_columns": first_binding.provenance.get("matched_columns") if first_binding.provenance else {},
                    "reason": first_binding.reason,
                }

            hist_ref = None
            if region and region.historical_reference:
                hist_ref = {
                    "doc_name": region.historical_reference.doc_name,
                    "table_index": region.historical_reference.table_index,
                    "correspondence": outcome.correspondence,
                }

            proposed_rows = []
            if table_spec and table_spec.row_mutations:
                for row_m in table_spec.row_mutations:
                    row_cells = []
                    for c in row_m.cells:
                        row_cells.append({
                            "col_idx": c.col_idx,
                            "source_sheet": c.source_sheet,
                            "source_cell_address": c.source_cell_address,
                            "value": c.value,
                        })
                    proposed_rows.append({
                        "row_idx": row_m.row_idx,
                        "cells": row_cells,
                    })

            template_content = {
                "initial_row_count": table_spec.initial_row_count if table_spec else (diff.before_summary.get("rows") if diff else None),
                "column_count": diff.before_summary.get("columns") if diff else None,
                "target_table_index": table_spec.table_index if table_spec else None,
            }

            proposed_content_desc = (
                f"+{table_spec.insert_count} dòng từ {first_binding.sheet_name}"
                if (table_spec and first_binding and first_binding.sheet_name)
                else ("; ".join(outcome.source_labels) if outcome.source_labels else "Chưa có đề xuất thay đổi")
            )

            proposal = {
                "id": f"prop-{idx + 1}",
                "region_id": outcome.region_id,
                "business_target": outcome.section_name,
                "target_region": f"Table {table_spec.table_index + 1}" if table_spec else outcome.section_name,
                "target_table_index": table_spec.table_index if table_spec else None,
                "target_table_hash": table_spec.table_hash if table_spec else None,
                "status": status,
                "status_label_vi": status_label_vi,
                "status_label_en": status_label_en,
                "source_evidence": src_evidence,
                "historical_reference": hist_ref,
                "template_content": template_content,
                "proposed_content": proposed_content_desc,
                "proposed_rows": proposed_rows,
                "rationale": "; ".join(outcome.reasons) if outcome.reasons else "Được xác định theo quy tắc roll-forward.",
                "binding_verdict": outcome.binding_verdict,
                "correspondence_score": outcome.correspondence,
                "decision": session["decisions"].get(f"prop-{idx + 1}", "PENDING"),
            }
            proposals.append(proposal)

        # Build status counts
        counts = {
            "MAPPED": sum(1 for p in proposals if p["status"] == "MAPPED"),
            "NEEDS_CONFIRMATION": sum(1 for p in proposals if p["status"] == "NEEDS_CONFIRMATION"),
            "MISSING_SOURCE": sum(1 for p in proposals if p["status"] == "MISSING_SOURCE"),
            "UNSUPPORTED": sum(1 for p in proposals if p["status"] == "UNSUPPORTED"),
        }

        review_projection = {
            "session_id": session_id,
            "template_doc_id": tmpl_id,
            "template_filename": tmpl_doc["filename"],
            "historical_doc_id": hist_id,
            "historical_filename": hist_doc["filename"],
            "current_source_doc_ids": [s["doc_id"] for s in src_docs],
            "current_source_filenames": [s["filename"] for s in src_docs],
            "historical_period": hist_period.label,
            "current_period": curr_period.label,
            "summary": {
                "total": len(proposals),
                "mapped": counts["MAPPED"],
                "needs_confirmation": counts["NEEDS_CONFIRMATION"],
                "missing_source": counts["MISSING_SOURCE"],
                "unsupported": counts["UNSUPPORTED"],
            },
            "proposals": proposals,
            "governance": {
                "docx_mutated": False,
                "approved_change_set_created": False,
                "replay_executed": False,
                "statement": "Bản xem trước thay đổi đề xuất. Chưa ghi vào tệp DOCX.",
            },
        }

        session["analysis_result"] = review_projection
        return jsonify(review_projection)


# ============================================================================
# 3. DOCUMENT CONTENT & ELEMENTS STREAMING
# ============================================================================

@demo_bp.route("/demo/gtps/documents/<doc_id>/content", methods=["GET"])
@demo_bp.route("/api/demo/gtps/documents/<doc_id>/content", methods=["GET"])
def stream_document_content(doc_id: str):
    """Streams the verified original document binary bytes for client rendering."""
    # Locate session containing doc_id
    target_session = None
    doc_info = None
    for s in _DEMO_SESSIONS.values():
        if doc_id in s["documents"]:
            target_session = s
            doc_info = s["documents"][doc_id]
            break

    if not target_session or not doc_info:
        return jsonify({"error": f"Unknown doc_id '{doc_id}'"}), 404

    storage = get_storage()
    user_id = _get_user_id()
    try:
        data = storage.get_document_bytes(target_session["session_id"], doc_id, user_id=user_id)
    except Exception as exc:
        return jsonify({"error": f"Failed to retrieve document: {exc}"}), 500

    filename = doc_info["filename"]
    mime, _ = mimetypes.guess_type(filename)
    if not mime:
        if filename.endswith(".docx"):
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".xlsx"):
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.endswith(".pdf"):
            mime = "application/pdf"
        else:
            mime = "application/octet-stream"

    return send_file(
        io.BytesIO(data),
        mimetype=mime,
        as_attachment=False,
        download_name=filename,
    )


@demo_bp.route("/demo/gtps/documents/<doc_id>/elements", methods=["GET"])
@demo_bp.route("/api/demo/gtps/documents/<doc_id>/elements", methods=["GET"])
def get_document_elements(doc_id: str):
    """Returns perceived elements for a document (used by XlsxRenderer)."""
    target_session = None
    doc_info = None
    for s in _DEMO_SESSIONS.values():
        if doc_id in s["documents"]:
            target_session = s
            doc_info = s["documents"][doc_id]
            break

    if not target_session or not doc_info:
        return jsonify({"error": f"Unknown doc_id '{doc_id}'"}), 404

    storage = get_storage()
    user_id = _get_user_id()
    try:
        with storage.get_document_path(target_session["session_id"], doc_id, user_id=user_id) as p:
            fmt = doc_info["format"]
            blocks = extract_geometry(str(p))
            anchors = assign_anchors(blocks, fmt)
            elements = classify_blocks(blocks, fmt, anchors)
            return jsonify({
                "doc_id": doc_id,
                "elements": [e.model_dump(mode="json") for e in elements],
            })
    except Exception as exc:
        return jsonify({"error": f"Failed to extract elements: {exc}"}), 500


# ============================================================================
# 4. REVIEW PROJECTION & PROTOTYPE REVIEW DECISION
# ============================================================================

@demo_bp.route("/demo/gtps/review", methods=["GET"])
@demo_bp.route("/api/demo/gtps/review", methods=["GET"])
def get_review_projection():
    """Returns the current mapping/review projection for the given session."""
    session_id = request.args.get("session_id")
    if not session_id or session_id not in _DEMO_SESSIONS:
        return jsonify({"error": "Unknown session_id"}), 404

    session = _DEMO_SESSIONS[session_id]
    if not session.get("analysis_result"):
        return jsonify({"error": "No analysis result available. Run /analyze first."}), 404

    return jsonify(session["analysis_result"])


@demo_bp.route("/demo/gtps/review/decision", methods=["POST"])
@demo_bp.route("/api/demo/gtps/review/decision", methods=["POST"])
def record_review_decision():
    """Records prototype review decision (Accept, Edit, Skip, Request Evidence).

    Explicitly labeled as prototype review state; does NOT mutate DOCX.
    """
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id")
    proposal_id = body.get("proposal_id")
    decision = body.get("decision")  # APPROVED | EDITED | SKIPPED | REJECTED | PENDING
    notes = body.get("notes") or ""

    if not session_id or session_id not in _DEMO_SESSIONS:
        return jsonify({"error": "Unknown session_id"}), 404

    session = _DEMO_SESSIONS[session_id]
    session["decisions"][proposal_id] = decision

    if session.get("analysis_result") and "proposals" in session["analysis_result"]:
        for p in session["analysis_result"]["proposals"]:
            if p["id"] == proposal_id:
                p["decision"] = decision
                if notes:
                    p["reviewer_notes"] = notes

    return jsonify({
        "session_id": session_id,
        "proposal_id": proposal_id,
        "decision": decision,
        "governance": {
            "docx_mutated": False,
            "statement": "Prototype review state recorded. Zero binary mutation performed.",
        }
    })

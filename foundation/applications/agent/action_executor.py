"""
Action Executor for Governed Agent Write Actions (Phase DEPLOY-1).
==================================================================
Location: foundation/applications/agent/action_executor.py

Executes confirmed write proposals strictly server-side by action_id.
Re-validates freshness via SHA-256 document hashing, checks capabilities,
executes Foundation WritebackEngine, logs cryptographic lineage, and updates
lifecycle state. Compatible with both DocumentStorage and local session dirs.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from applications.agent.proposal_store import ProposalStore
from applications.pilot.event_log import PilotEventLogger
from perception.models import Anchor, Element
from perception.parser import extract_geometry
from perception.anchor_builder import assign_anchors
from perception.element_classifier import classify_blocks
from output.lineage import LineageLogger
from output.writeback import WritebackEngine
from adapters.storage import get_storage
from adapters.repository import DocumentVersionRecord, LineageEventRecord, get_repositories

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


def _current_path_for_dir(session_dir: Path, entry: dict) -> Path:
    stored_path = session_dir / entry["stored_filename"]
    patched = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
    return patched if patched.exists() else stored_path


class ActionExecutor:
    """Executes server-side validated action proposals."""

    @classmethod
    def execute_confirmed_action(cls, session_id: str, action_id: str, user_id: str = "anonymous") -> dict[str, Any]:
        storage = get_storage()
        repos = get_repositories()

        # 1. Atomically validate and claim proposal (transitions status to 'executing')
        proposal = ProposalStore.claim_proposal_for_execution(session_id, action_id, user_id=user_id)

        session_dir = UPLOAD_ROOT / session_id
        entry = None
        if session_dir.is_dir():
            manifest_path = session_dir / "manifest.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    entry = manifest.get("documents", {}).get(proposal.doc_id)
                except Exception:
                    pass

        # Retrieve document record or fallback to local manifest
        doc = repos.documents.get_document(session_id, proposal.doc_id, user_id=user_id)
        fmt = (entry.get("format") if entry else None) or (doc.format if doc else None)
        orig_filename = (entry.get("original_filename") if entry else None) or (doc.original_filename if doc else None)

        if not fmt:
            raise ValueError(f"Document '{proposal.doc_id}' not found in session '{session_id}'.")

        # Local directory direct execution (for seeded tests and local dev)
        if session_dir.is_dir() and entry:
            current_path = _current_path_for_dir(session_dir, entry)
            if not current_path.exists():
                raise ValueError(f"Document file '{current_path.name}' not found on disk.")

            current_bytes = current_path.read_bytes()
            current_hash = hashlib.sha256(current_bytes).hexdigest()

            if proposal.doc_hash and current_hash != proposal.doc_hash:
                ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                PilotEventLogger.emit(
                    "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="doc_hash_mismatch",
                )
                raise ValueError(
                    f"Document content has changed out-of-band since proposal creation "
                    f"(expected hash: {proposal.doc_hash[:8]}, current: {current_hash[:8]}). "
                    "A fresh proposal must be generated."
                )

            # Resolve anchor
            anchor: Anchor | None = None
            if proposal.target_anchor:
                try:
                    anchor = Anchor(**proposal.target_anchor)
                except Exception:
                    anchor = None

            if not anchor:
                blocks = extract_geometry(str(current_path))
                anchors = assign_anchors(blocks, fmt)
                elements = classify_blocks(blocks, fmt, anchors)

                target_el: Element | None = None
                for el in elements:
                    if el.element_id == proposal.element_id:
                        target_el = el
                        break

                if not target_el:
                    ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                    PilotEventLogger.emit(
                        "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="element_missing",
                    )
                    raise ValueError(f"Target element '{proposal.element_id}' no longer exists in document.")

                if not target_el.capabilities.editable:
                    raise ValueError(f"Target element '{target_el.name}' is read-only (capabilities.editable is false).")

                if target_el.text != proposal.current_value:
                    ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                    PilotEventLogger.emit(
                        "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="content_changed",
                    )
                    raise ValueError(
                        f"Element content has changed since the proposal was created "
                        f"(expected: '{proposal.current_value[:40]}...', found: '{target_el.text[:40]}...'). "
                        "A fresh proposal must be generated."
                    )
                anchor = target_el.anchor

            stored_stem = Path(entry["stored_filename"]).stem
            stored_suffix = Path(entry["stored_filename"]).suffix
            patched_path = session_dir / f"{stored_stem}_patched{stored_suffix}"

            engine = WritebackEngine()
            self_heal = engine.apply_single_patch(
                str(current_path),
                anchor,
                proposal.proposed_value,
                str(patched_path),
            )

            # Log Lineage locally
            logger = LineageLogger(log_dir=str(session_dir / "lineage"))
            logger.log_mapping(
                target_anchor=anchor.model_dump_json(),
                target_value=proposal.proposed_value,
                source_file="Agent:governed_proposal",
                source_anchor=f"action:{action_id}",
                confidence=1.0,
            )

            # Mark proposal applied
            ProposalStore.update_proposal_status(session_id, action_id, "applied", user_id=user_id)
            download_url = f"/api/documents/{session_id}/download/{proposal.doc_id}"

            return {
                "status": "success",
                "action_id": action_id,
                "doc_id": proposal.doc_id,
                "element_id": proposal.element_id,
                "old_value": proposal.current_value,
                "new_value": proposal.proposed_value,
                "download_url": download_url,
                "self_heal": self_heal,
            }

        # Remote / Storage-backed execution path
        is_already_patched = storage.document_exists(session_id, proposal.doc_id, is_patched=True, user_id=user_id)

        with storage.get_document_path(session_id, proposal.doc_id, is_patched=is_already_patched, user_id=user_id) as current_path:
            current_bytes = current_path.read_bytes()
            current_hash = hashlib.sha256(current_bytes).hexdigest()

            if proposal.doc_hash and current_hash != proposal.doc_hash:
                ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                PilotEventLogger.emit(
                    "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="doc_hash_mismatch",
                )
                raise ValueError(
                    f"Document content has changed out-of-band since proposal creation "
                    f"(expected hash: {proposal.doc_hash[:8]}, current: {current_hash[:8]}). "
                    "A fresh proposal must be generated."
                )

            # 2. Resolve Anchor
            anchor: Anchor | None = None
            if proposal.target_anchor:
                try:
                    anchor = Anchor(**proposal.target_anchor)
                except Exception:
                    anchor = None

            if not anchor:
                blocks = extract_geometry(str(current_path))
                anchors = assign_anchors(blocks, fmt)
                elements = classify_blocks(blocks, fmt, anchors)

                target_el: Element | None = None
                for el in elements:
                    if el.element_id == proposal.element_id:
                        target_el = el
                        break

                if not target_el:
                    ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                    PilotEventLogger.emit(
                        "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="element_missing",
                    )
                    raise ValueError(f"Target element '{proposal.element_id}' no longer exists in document.")

                if not target_el.capabilities.editable:
                    raise ValueError(f"Target element '{target_el.name}' is read-only (capabilities.editable is false).")

                if target_el.text != proposal.current_value:
                    ProposalStore.update_proposal_status(session_id, action_id, "stale", user_id=user_id)
                    PilotEventLogger.emit(
                        "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="content_changed",
                    )
                    raise ValueError(
                        f"Element content has changed since the proposal was created "
                        f"(expected: '{proposal.current_value[:40]}...', found: '{target_el.text[:40]}...'). "
                        "A fresh proposal must be generated."
                    )
                anchor = target_el.anchor

            # 3. Execute WritebackEngine
            temp_out = tempfile.NamedTemporaryFile(delete=False, suffix=current_path.suffix)
            temp_out_path = Path(temp_out.name)
            temp_out.close()

            try:
                engine = WritebackEngine()
                self_heal = engine.apply_single_patch(
                    str(current_path),
                    anchor,
                    proposal.proposed_value,
                    str(temp_out_path),
                )
                patched_bytes = temp_out_path.read_bytes()
            finally:
                if temp_out_path.exists():
                    try:
                        temp_out_path.unlink()
                    except OSError:
                        pass

        # 4. Save patched bytes to Storage
        filename = orig_filename or f"doc.{fmt}"
        storage_res = storage.save_document(
            session_id=session_id,
            doc_id=proposal.doc_id,
            filename=filename,
            data=patched_bytes,
            is_patched=True,
            user_id=user_id,
        )

        # 5. Log version
        latest = repos.documents.get_latest_version(session_id, proposal.doc_id, user_id=user_id)
        next_ver = (latest.version_number + 1) if latest else 2
        repos.documents.create_version(
            DocumentVersionRecord(
                version_id=str(tempfile.NamedTemporaryFile().name),
                doc_id=proposal.doc_id,
                session_id=session_id,
                user_id=user_id,
                version_number=next_ver,
                sha256=storage_res.file_hash,
                storage_path=storage_res.storage_path,
                is_patched=True,
                size_bytes=storage_res.size_bytes,
            )
        )

        # 6. Log Lineage
        repos.lineage.log_mapping(
            LineageEventRecord(
                session_id=session_id,
                user_id=user_id,
                target_anchor=anchor.model_dump_json(),
                target_value_hash=storage_res.file_hash,
                source_file="Agent:governed_proposal",
                source_anchor=f"action:{action_id}",
                confidence=1.0,
            )
        )

        # 7. Mark proposal applied
        ProposalStore.update_proposal_status(session_id, action_id, "applied", user_id=user_id)

        download_url = f"/api/documents/{session_id}/download/{proposal.doc_id}"

        return {
            "status": "success",
            "action_id": action_id,
            "doc_id": proposal.doc_id,
            "element_id": proposal.element_id,
            "old_value": proposal.current_value,
            "new_value": proposal.proposed_value,
            "download_url": download_url,
            "self_heal": self_heal,
        }

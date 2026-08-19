"""Action Executor for Governed Agent Write Actions (Slice 5 & 6).

Executes confirmed write proposals strictly server-side by action_id.
Re-validates freshness via SHA-256 document hashing, checks capabilities,
executes Foundation WritebackEngine, logs cryptographic lineage, and updates
lifecycle state.
"""
from __future__ import annotations

import hashlib
import json
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

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


class ActionExecutor:
    """Executes server-side validated action proposals."""

    @classmethod
    def execute_confirmed_action(cls, session_id: str, action_id: str) -> dict[str, Any]:
        session_dir = UPLOAD_ROOT / session_id
        if not session_dir.is_dir():
            raise ValueError(f"Invalid session or action proposal not found for session_id '{session_id}'.")

        # 1. Atomically validate and claim proposal (transitions status to 'executing')
        proposal = ProposalStore.claim_proposal_for_execution(session_id, action_id)

        manifest_path = session_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("Session manifest missing.")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entry = manifest.get("documents", {}).get(proposal.doc_id)
        if not entry:
            raise ValueError(f"Document '{proposal.doc_id}' not found in session.")

        stored_path = session_dir / entry["stored_filename"]
        patched_path = stored_path.with_name(f"{stored_path.stem}_patched{stored_path.suffix}")
        current_path = patched_path if patched_path.exists() else stored_path
        fmt = entry["format"]

        if not current_path.exists():
            raise ValueError(f"Document file '{current_path.name}' not found on disk.")

        # 1. Freshness Check: Validate SHA-256 document content hash
        current_bytes = current_path.read_bytes()
        current_hash = hashlib.sha256(current_bytes).hexdigest()

        if proposal.doc_hash and current_hash != proposal.doc_hash:
            ProposalStore.update_proposal_status(session_id, action_id, "stale")
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
            # Fallback to perceiving elements if target_anchor was not pre-computed
            blocks = extract_geometry(str(current_path))
            anchors = assign_anchors(blocks, fmt)
            elements = classify_blocks(blocks, fmt, anchors)

            target_el: Element | None = None
            for el in elements:
                if el.element_id == proposal.element_id:
                    target_el = el
                    break

            if not target_el:
                ProposalStore.update_proposal_status(session_id, action_id, "stale")
                PilotEventLogger.emit(
                    "agent.proposal.stale", session_id=session_id, action_id=action_id, reason="element_missing",
                )
                raise ValueError(f"Target element '{proposal.element_id}' no longer exists in document.")

            if not target_el.capabilities.editable:
                raise ValueError(f"Target element '{target_el.name}' is read-only (capabilities.editable is false).")

            if target_el.text != proposal.current_value:
                ProposalStore.update_proposal_status(session_id, action_id, "stale")
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
        engine = WritebackEngine()
        self_heal = engine.apply_single_patch(
            str(current_path),
            anchor,
            proposal.proposed_value,
            str(patched_path),
        )

        # 4. Log Lineage with cryptographic hash (session-scoped log dir)
        logger = LineageLogger(log_dir=str(session_dir / "lineage"))
        logger.log_mapping(
            target_anchor=anchor.model_dump_json(),
            target_value=proposal.proposed_value,
            source_file="Agent:governed_proposal",
            source_anchor=f"action:{action_id}",
            confidence=1.0,
        )

        # 5. Mark proposal applied (strict error propagation)
        ProposalStore.update_proposal_status(session_id, action_id, "applied")

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

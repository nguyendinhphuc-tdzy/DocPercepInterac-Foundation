"""Action Executor for Governed Agent Write Actions (Slice 5 & 6).

Executes confirmed write proposals strictly server-side by action_id.
Re-validates freshness, capabilities, and executes Foundation WritebackEngine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from applications.agent.proposal_store import ProposalStore
from perception.models import Element
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
        proposal = ProposalStore.get_proposal(session_id, action_id)
        if not proposal:
            raise ValueError(f"Action proposal '{action_id}' not found or has expired.")

        if proposal.status == "applied":
            raise ValueError(f"Action proposal '{action_id}' has already been applied.")

        if proposal.status == "rejected":
            raise ValueError(f"Action proposal '{action_id}' was rejected.")

        session_dir = UPLOAD_ROOT / session_id
        if not session_dir.is_dir():
            raise ValueError(f"Unknown session_id '{session_id}'")

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

        # Perceive current document elements to validate freshness and capabilities
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
            raise ValueError(f"Target element '{proposal.element_id}' no longer exists in document.")

        if not target_el.capabilities.editable:
            raise ValueError(f"Target element '{target_el.name}' is read-only (capabilities.editable is false).")

        # Validate freshness: ensure content hasn't changed since proposal
        if target_el.text != proposal.current_value:
            ProposalStore.update_proposal_status(session_id, action_id, "stale")
            raise ValueError(
                f"Element content has changed since the proposal was created "
                f"(expected: '{proposal.current_value[:40]}...', found: '{target_el.text[:40]}...'). "
                "A fresh proposal must be generated."
            )

        # Execute WritebackEngine
        engine = WritebackEngine()
        self_heal = engine.apply_single_patch(
            str(current_path),
            target_el.anchor,
            proposal.proposed_value,
            str(patched_path),
        )

        # Log Lineage
        logger = LineageLogger()
        logger.log_mapping(
            target_anchor=target_el.anchor.model_dump_json(),
            target_value=proposal.proposed_value,
            source_file="Agent:governed_proposal",
            source_anchor=f"action:{action_id}",
            confidence=1.0,
        )

        # Mark proposal applied
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

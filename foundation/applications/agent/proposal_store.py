"""Server-side Proposal Store for Governed Agent Write Actions.

Stores proposed actions associated with action_id so execution never trusts
client-rewritten parameters.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from applications.agent.models import ProposedAction

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


class ProposalStore:
    """Manages persistence and retrieval of server-side action proposals."""

    @staticmethod
    def _proposals_path(session_id: str) -> Path:
        session_dir = UPLOAD_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / "agent_proposals.json"

    @classmethod
    def save_proposal(cls, session_id: str, proposal: ProposedAction) -> None:
        path = cls._proposals_path(session_id)
        proposals = {}
        if path.exists():
            try:
                proposals = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                proposals = {}

        proposals[proposal.action_id] = proposal.model_dump(mode="json")
        path.write_text(json.dumps(proposals, indent=2), encoding="utf-8")

    @classmethod
    def get_proposal(cls, session_id: str, action_id: str) -> Optional[ProposedAction]:
        path = cls._proposals_path(session_id)
        if not path.exists():
            return None
        try:
            proposals = json.loads(path.read_text(encoding="utf-8"))
            raw = proposals.get(action_id)
            if not raw:
                return None
            return ProposedAction(**raw)
        except Exception:
            return None

    @classmethod
    def update_proposal_status(cls, session_id: str, action_id: str, status: str) -> None:
        path = cls._proposals_path(session_id)
        if not path.exists():
            return
        try:
            proposals = json.loads(path.read_text(encoding="utf-8"))
            if action_id in proposals:
                proposals[action_id]["status"] = status
                path.write_text(json.dumps(proposals, indent=2), encoding="utf-8")
        except Exception:
            pass

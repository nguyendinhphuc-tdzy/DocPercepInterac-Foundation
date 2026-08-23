"""
Server-side Proposal Store for Governed Agent Write Actions (Phase DEPLOY-1).
=============================================================================
Location: foundation/applications/agent/proposal_store.py

Manages persistence, lifecycle, and atomic retrieval of server-side action
proposals. Delegates to the repository abstraction layer (Local or Supabase),
preserving concurrency safety, session isolation, replay prevention, and TTL tracking.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.agent.models import ProposedAction  # noqa: E402
from adapters.repository import ProposalRecord, get_repositories  # noqa: E402

# Preserved for backward-compatibility in legacy test monkeypatching
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


class ProposalStore:
    """Manages persistence, lifecycle, and retrieval of server-side action proposals."""

    @classmethod
    def _to_record(cls, session_id: str, proposal: ProposedAction, user_id: str = "anonymous") -> ProposalRecord:
        return ProposalRecord(
            action_id=proposal.action_id,
            session_id=session_id,
            user_id=user_id,
            doc_id=proposal.doc_id,
            doc_name=proposal.doc_name,
            element_id=proposal.element_id,
            element_name=proposal.element_name,
            type=proposal.type,
            requires_confirmation=proposal.requires_confirmation,
            proposed_value=proposal.proposed_value,
            target_anchor=proposal.target_anchor,
            current_value=proposal.current_value,
            rationale=proposal.rationale,
            doc_hash=proposal.doc_hash,
            value_fingerprint=proposal.value_fingerprint,
            status=proposal.status,
            ttl_seconds=proposal.ttl_seconds,
            created_at=proposal.created_at,
        )

    @classmethod
    def _from_record(cls, record: ProposalRecord) -> ProposedAction:
        return ProposedAction(
            action_id=record.action_id,
            doc_id=record.doc_id,
            doc_name=record.doc_name or "document",
            element_id=record.element_id,
            element_name=record.element_name or "element",
            type=record.type,
            requires_confirmation=record.requires_confirmation,
            proposed_value=record.proposed_value,
            target_anchor=record.target_anchor,
            current_value=record.current_value or "",
            rationale=record.rationale or "",
            doc_hash=record.doc_hash,
            value_fingerprint=record.value_fingerprint,
            status=record.status,
            ttl_seconds=record.ttl_seconds,
            created_at=record.created_at,
        )

    @classmethod
    def save_proposal(cls, session_id: str, proposal: ProposedAction, user_id: str = "anonymous") -> None:
        repos = get_repositories()
        rec = cls._to_record(session_id, proposal, user_id=user_id)
        repos.proposals.save_proposal(rec)

    @classmethod
    def get_proposal(cls, session_id: str, action_id: str, user_id: str = "anonymous") -> Optional[ProposedAction]:
        repos = get_repositories()
        rec = repos.proposals.get_proposal(session_id, action_id, user_id=user_id)
        return cls._from_record(rec) if rec else None

    @classmethod
    def claim_proposal_for_execution(cls, session_id: str, action_id: str, user_id: str = "anonymous") -> ProposedAction:
        """Atomically validates and claims a proposal for execution, transitioning status to 'executing'."""
        repos = get_repositories()
        rec = repos.proposals.claim_proposal_for_execution(session_id, action_id, user_id=user_id)
        return cls._from_record(rec)

    @classmethod
    def update_proposal_status(cls, session_id: str, action_id: str, status: str, user_id: str = "anonymous") -> None:
        """Updates proposal status. Raises ValueError/RuntimeError if update fails."""
        repos = get_repositories()
        repos.proposals.update_proposal_status(session_id, action_id, status, user_id=user_id)

    @classmethod
    def cleanup_stale_proposals(cls, session_id: str, user_id: str = "anonymous") -> int:
        """Marks all expired proposals in session as 'expired'. Returns count marked."""
        repos = get_repositories()
        return repos.proposals.cleanup_stale_proposals(session_id, user_id=user_id)

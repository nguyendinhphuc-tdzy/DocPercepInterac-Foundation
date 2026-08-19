"""Server-side Proposal Store for Governed Agent Write Actions.

Stores proposed actions associated with action_id so execution never trusts
client-rewritten parameters. Uses file-locking and atomic replacement for
concurrency safety, session isolation, and lifecycle/TTL tracking.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import tempfile
from typing import Optional

from filelock import FileLock

from applications.agent.models import ProposedAction
from applications.pilot.event_log import PilotEventLogger

UPLOAD_ROOT = Path(__file__).resolve().parents[2] / ".uploads"


class ProposalStore:
    """Manages persistence, lifecycle, and retrieval of server-side action proposals."""

    @staticmethod
    def _proposals_path(session_id: str) -> Path:
        session_dir = UPLOAD_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / "agent_proposals.json"

    @staticmethod
    def _lock_path(session_id: str) -> Path:
        session_dir = UPLOAD_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / "agent_proposals.json.lock"

    @classmethod
    def _read_locked(cls, session_id: str) -> dict[str, dict]:
        path = cls._proposals_path(session_id)
        if not path.exists():
            return {}
        try:
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                return {}
            return json.loads(content)
        except Exception:
            return {}

    @classmethod
    def _write_locked(cls, session_id: str, data: dict[str, dict]) -> None:
        path = cls._proposals_path(session_id)
        session_dir = path.parent
        # Atomic replacement: write to tempfile in same dir, then replace
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=session_dir,
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        ) as tf:
            json.dump(data, tf, indent=2)
            temp_name = tf.name
        
        try:
            os.replace(temp_name, path)
        except Exception as exc:
            if os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except OSError:
                    pass
            raise RuntimeError(f"Failed to atomically persist proposals for session '{session_id}': {exc}") from exc

    @classmethod
    def save_proposal(cls, session_id: str, proposal: ProposedAction) -> None:
        lock = FileLock(str(cls._lock_path(session_id)), timeout=10)
        with lock:
            proposals = cls._read_locked(session_id)
            proposals[proposal.action_id] = proposal.model_dump(mode="json")
            cls._write_locked(session_id, proposals)

    @classmethod
    def get_proposal(cls, session_id: str, action_id: str) -> Optional[ProposedAction]:
        lock = FileLock(str(cls._lock_path(session_id)), timeout=10)
        with lock:
            proposals = cls._read_locked(session_id)
            raw = proposals.get(action_id)
            if not raw:
                return None
            
            proposal = ProposedAction(**raw)

            # Enforce TTL expiration
            try:
                created_dt = datetime.fromisoformat(proposal.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if now > (created_dt + timedelta(seconds=proposal.ttl_seconds)):
                    if proposal.status == "proposed":
                        proposal.status = "expired"
                        proposals[action_id]["status"] = "expired"
                        cls._write_locked(session_id, proposals)
                        PilotEventLogger.emit(
                            "agent.proposal.expired", session_id=session_id, action_id=action_id,
                        )
            except Exception:
                pass

            return proposal

    @classmethod
    def claim_proposal_for_execution(cls, session_id: str, action_id: str) -> ProposedAction:
        """Atomically validates and claims a proposal for execution under lock, transitioning status to 'executing'."""
        lock = FileLock(str(cls._lock_path(session_id)), timeout=10)
        with lock:
            proposals = cls._read_locked(session_id)
            raw = proposals.get(action_id)
            if not raw:
                raise ValueError(f"Action proposal '{action_id}' not found or has expired.")

            proposal = ProposedAction(**raw)

            # Check TTL
            try:
                created_dt = datetime.fromisoformat(proposal.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                if now > (created_dt + timedelta(seconds=proposal.ttl_seconds)):
                    proposal.status = "expired"
                    proposals[action_id]["status"] = "expired"
                    cls._write_locked(session_id, proposals)
                    PilotEventLogger.emit(
                        "agent.proposal.expired", session_id=session_id, action_id=action_id,
                    )
                    raise ValueError(f"Action proposal '{action_id}' has expired (TTL exceeded).")
            except Exception as exc:
                if "TTL exceeded" in str(exc):
                    raise

            if proposal.status == "applied":
                raise ValueError(f"Action proposal '{action_id}' has already been applied.")
            if proposal.status == "executing":
                raise ValueError(f"Action proposal '{action_id}' is already being executed.")
            if proposal.status == "rejected":
                raise ValueError(f"Action proposal '{action_id}' was rejected.")
            if proposal.status == "expired":
                raise ValueError(f"Action proposal '{action_id}' has expired (TTL exceeded).")
            if proposal.status == "stale":
                raise ValueError(f"Action proposal '{action_id}' is stale and cannot be executed.")
            if proposal.status != "proposed":
                raise ValueError(f"Action proposal '{action_id}' is not in 'proposed' state (status: '{proposal.status}').")

            # Atomically mark executing
            proposal.status = "executing"
            proposals[action_id]["status"] = "executing"
            cls._write_locked(session_id, proposals)

            return proposal

    @classmethod
    def update_proposal_status(cls, session_id: str, action_id: str, status: str) -> None:
        """Updates proposal status under lock. Raises RuntimeError if update fails."""
        lock = FileLock(str(cls._lock_path(session_id)), timeout=10)
        with lock:
            proposals = cls._read_locked(session_id)
            if action_id not in proposals:
                raise ValueError(f"Proposal '{action_id}' not found in session '{session_id}'.")
            proposals[action_id]["status"] = status
            cls._write_locked(session_id, proposals)

    @classmethod
    def cleanup_stale_proposals(cls, session_id: str) -> int:
        """Marks all expired proposals in session as 'expired'. Returns count marked."""
        lock = FileLock(str(cls._lock_path(session_id)), timeout=10)
        with lock:
            proposals = cls._read_locked(session_id)
            now = datetime.now(timezone.utc)
            updated_count = 0
            for action_id, raw in proposals.items():
                if raw.get("status") == "proposed":
                    try:
                        created_dt = datetime.fromisoformat(raw.get("created_at", ""))
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        ttl = raw.get("ttl_seconds", 86400)
                        if now > (created_dt + timedelta(seconds=ttl)):
                            raw["status"] = "expired"
                            updated_count += 1
                            PilotEventLogger.emit(
                                "agent.proposal.expired", session_id=session_id, action_id=action_id,
                            )
                    except Exception:
                        pass
            if updated_count > 0:
                cls._write_locked(session_id, proposals)
            return updated_count

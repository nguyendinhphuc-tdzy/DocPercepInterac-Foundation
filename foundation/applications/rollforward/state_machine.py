"""
Local File Roll-Forward Lifecycle State Machine (V1 Contract)
=============================================================
Location: foundation/applications/rollforward/state_machine.py

Enforces strict, governed lifecycle transitions for the Roll-Forward Manifest.
Prevents unapproved execution, enforces user-only approval provenance,
and manages review gating deterministically.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Set

from applications.rollforward.models import (
    ManifestStatus,
    RollForwardManifest,
    TransitionLog,
)


class RollForwardStateError(Exception):
    """Base exception for roll-forward state machine violations."""
    pass


class IllegalTransitionError(RollForwardStateError):
    """Raised when an illegal or out-of-order state transition is attempted."""
    pass


class UnauthorizedApprovalError(RollForwardStateError):
    """Raised when non-user actors (Agent, System) attempt to approve a manifest."""
    pass


class ApprovalInvalidationError(RollForwardStateError):
    """Raised when execution is attempted on an unapproved or modified manifest."""
    pass


class RollForwardStateMachine:
    """Deterministic, immutable state transition controller for RollForwardManifest."""

    # Explicit legal transition graph
    LEGAL_TRANSITIONS: Dict[ManifestStatus, Set[ManifestStatus]] = {
        ManifestStatus.DISCOVERED: {
            ManifestStatus.PLANNED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.PLANNED: {
            ManifestStatus.REVIEW_REQUIRED,
            ManifestStatus.APPROVED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.REVIEW_REQUIRED: {
            ManifestStatus.APPROVED,
            ManifestStatus.PLANNED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.APPROVED: {
            ManifestStatus.EXECUTING,
            ManifestStatus.PLANNED,
            ManifestStatus.REVIEW_REQUIRED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.EXECUTING: {
            ManifestStatus.VALIDATED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.VALIDATED: {
            ManifestStatus.COMPLETED,
            ManifestStatus.REQUIRES_MANUAL_REVIEW,
            ManifestStatus.FAILED,
        },
        ManifestStatus.REQUIRES_MANUAL_REVIEW: {
            ManifestStatus.REVIEW_REQUIRED,
            ManifestStatus.PLANNED,
            ManifestStatus.FAILED,
        },
        ManifestStatus.FAILED: {
            ManifestStatus.PLANNED,
            ManifestStatus.DISCOVERED,
        },
        ManifestStatus.COMPLETED: set(),  # Terminal state
    }

    @classmethod
    def transition(
        cls,
        manifest: RollForwardManifest,
        target_status: ManifestStatus,
        actor: Literal["user", "agent", "system"],
        reason: str = "",
        approved_by: Optional[str] = None,
    ) -> RollForwardManifest:
        """Executes a governed state transition on the manifest.

        Args:
            manifest: The RollForwardManifest instance to transition.
            target_status: The intended next ManifestStatus.
            actor: The entity initiating the transition ('user', 'agent', 'system').
            reason: Human-readable rationale for this transition.
            approved_by: Explicit user identifier (required when target is APPROVED).

        Returns:
            The mutated manifest with updated status, timestamps, and transition log.

        Raises:
            IllegalTransitionError: If the transition is not in the legal transition graph.
            UnauthorizedApprovalError: If an approval is attempted by a non-user actor.
            ApprovalInvalidationError: If execution is attempted without proper approval.
        """
        current_status = manifest.status

        # 1. Validate against legal transition graph
        allowed_targets = cls.LEGAL_TRANSITIONS.get(current_status, set())
        if target_status not in allowed_targets:
            raise IllegalTransitionError(
                f"Illegal state transition from {current_status.value} to {target_status.value}. "
                f"Allowed transitions from {current_status.value}: "
                f"{[s.value for s in allowed_targets]}"
            )

        # 2. Strict Approval Gating Rules
        if target_status == ManifestStatus.APPROVED:
            if actor != "user":
                raise UnauthorizedApprovalError(
                    f"Only explicit user action can approve a Roll-Forward Manifest. "
                    f"Attempted by actor: '{actor}'."
                )
            if manifest.has_unresolved_reviews() and current_status == ManifestStatus.PLANNED:
                # If unresolved reviews exist, cannot jump directly from PLANNED to APPROVED;
                # must route through REVIEW_REQUIRED first.
                raise IllegalTransitionError(
                    "Manifest contains regions or figures requiring manual review. "
                    "Must transition to REVIEW_REQUIRED before approval."
                )

            # Record approval provenance
            user_id = approved_by or "user-authenticated"
            manifest.approved_by = user_id
            manifest.approved_at = datetime.now(timezone.utc).isoformat()
            manifest.approved_manifest_version = manifest.manifest_version

        # 3. Strict Execution Gating Rules
        if target_status == ManifestStatus.EXECUTING:
            if not manifest.is_execution_ready():
                raise ApprovalInvalidationError(
                    f"Manifest {manifest.manifest_id} (version {manifest.manifest_version}) "
                    f"is not execution-ready. Status must be APPROVED and all regions must be READY."
                )

        # 4. Apply transition
        manifest.status = target_status
        manifest.updated_at = datetime.now(timezone.utc).isoformat()

        # 5. Append immutable transition log
        log_entry = TransitionLog(
            from_state=current_status,
            to_state=target_status,
            actor=actor,
            reason=reason or f"Transitioned from {current_status.value} to {target_status.value}.",
            manifest_version=manifest.manifest_version,
        )
        manifest.history.append(log_entry)

        return manifest

    @classmethod
    def approve(
        cls,
        manifest: RollForwardManifest,
        user_name: str,
        reason: str = "User approved roll-forward execution plan.",
    ) -> RollForwardManifest:
        """Helper to record user approval with strict provenance."""
        return cls.transition(
            manifest=manifest,
            target_status=ManifestStatus.APPROVED,
            actor="user",
            reason=reason,
            approved_by=user_name,
        )

    @classmethod
    def start_execution(
        cls,
        manifest: RollForwardManifest,
        actor: Literal["user", "system"] = "system",
        reason: str = "Starting structural writeback execution.",
    ) -> RollForwardManifest:
        """Helper to begin execution."""
        return cls.transition(
            manifest=manifest,
            target_status=ManifestStatus.EXECUTING,
            actor=actor,
            reason=reason,
        )

    @classmethod
    def mark_validated(
        cls,
        manifest: RollForwardManifest,
        reason: str = "Post-generation validation passed.",
    ) -> RollForwardManifest:
        """Helper to mark execution validated."""
        return cls.transition(
            manifest=manifest,
            target_status=ManifestStatus.VALIDATED,
            actor="system",
            reason=reason,
        )

    @classmethod
    def mark_completed(
        cls,
        manifest: RollForwardManifest,
        actor: Literal["user", "system"] = "system",
        reason: str = "Roll-forward workflow completed successfully.",
    ) -> RollForwardManifest:
        """Helper to mark workflow completed."""
        return cls.transition(
            manifest=manifest,
            target_status=ManifestStatus.COMPLETED,
            actor=actor,
            reason=reason,
        )

    @classmethod
    def mark_failed(
        cls,
        manifest: RollForwardManifest,
        error_message: str,
        actor: Literal["agent", "system", "user"] = "system",
    ) -> RollForwardManifest:
        """Helper to record failure."""
        return cls.transition(
            manifest=manifest,
            target_status=ManifestStatus.FAILED,
            actor=actor,
            reason=error_message,
        )

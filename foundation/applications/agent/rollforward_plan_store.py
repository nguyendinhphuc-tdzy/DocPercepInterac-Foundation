"""
Governed roll-forward plans, and the approval that executes one (Phase PROD-RF-1)
================================================================================
Location: foundation/applications/agent/rollforward_plan_store.py

A roll-forward plan is not something the Agent composes. It is a pair of governed
artifacts produced by the planning layer:

    RollForwardManifest  — which regions change, and which source cell each value
                           comes from (region profiling + source binding)
    MutationPlan         — the exact cell writes and row inserts to perform

This module is the seam between those artifacts and the Agent:

    register()  the planning layer hands over a plan for one session
    get()       the Agent asks whether these documents have a plan
    approve_and_execute()
                the ONLY path to a real execution, and it goes straight to
                RollForwardOrchestrator

Two properties matter more than convenience here:

    A plan is bound to the documents it was built from. `binding_mismatches()`
    re-checks that binding against the workflow's current slots, so a plan can
    never be executed against a file that was swapped after it was made.

    Nothing here produces a plan. If the planning layer has not run for a
    session, there is no plan, the Agent says so, and approval is refused.
    Inventing a plausible plan would be the same defect as inventing a result.

Storage note: plans live in memory for the life of the process. They are
pre-approval working artifacts — the governed record of what happened is the
execution report and its lineage, which the orchestrator persists. A plan that
is lost to a restart is simply re-planned; it is never silently reused.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from applications.rollforward.models import ManifestStatus, RollForwardManifest
from applications.rollforward.workflow_intake import SlotId, WorkflowIntakeSession


class RollForwardApprovalError(RuntimeError):
    """Raised when execution is asked for and may not be given."""


@dataclass
class GovernedPlan:
    """One governed plan, bound to the exact documents it was built from."""
    plan_id: str
    session_id: str
    user_id: str
    manifest: RollForwardManifest
    mutation_plan: Any                     # applications.rollforward.MutationPlan
    template_path: Path
    output_path: Path
    source_paths: List[Path] = field(default_factory=list)
    expected_template_hash: str = ""
    expected_source_hashes: Dict[str, str] = field(default_factory=dict)
    # Which workflow documents this plan was built from — the binding contract.
    historical_document_id: Optional[str] = None
    template_document_id: Optional[str] = None
    current_source_document_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # -- binding ---------------------------------------------------------

    def binding_mismatches(self, session: WorkflowIntakeSession) -> List[str]:
        """Reasons this plan does not describe the workflow's current documents.

        Checked by document id, which is content-addressed upstream: replacing a
        file in a slot gives it a new id, so a stale plan cannot silently apply
        to the new file.
        """
        context = session.agent_workflow_context()
        problems: List[str] = []

        if self.historical_document_id != context["historical_document_id"]:
            problems.append(
                "The plan was built for a different Previous Local File than the one now "
                "in the workflow.")
        if self.template_document_id != context["template_document_id"]:
            problems.append(
                "The plan was built for a different Master Template than the one now in "
                "the workflow.")
        if sorted(self.current_source_document_ids) != sorted(
                context["current_source_document_ids"]):
            problems.append(
                "The current-year sources have changed since the plan was built.")
        return problems

    # -- preview ---------------------------------------------------------

    def preview(self) -> Dict[str, Any]:
        """Counts read out of the mutation plan itself — never estimated."""
        tables = list(getattr(self.mutation_plan, "table_mutations", []) or [])
        rows = sum(len(getattr(t, "row_mutations", []) or []) for t in tables)
        cells = sum(len(getattr(row, "cells", []) or [])
                    for t in tables for row in getattr(t, "row_mutations", []) or [])
        regions = {getattr(t, "target_region_id", None) for t in tables} - {None}

        return {
            "plan_id": getattr(self.mutation_plan, "plan_id", self.plan_id),
            "manifest_id": self.manifest.manifest_id,
            "manifest_version": self.manifest.manifest_version,
            "manifest_status": str(getattr(self.manifest.status, "value",
                                           self.manifest.status)),
            "regions_in_plan": len(regions),
            "tables_to_update": len(tables),
            "cells_to_update": cells,
            "rows_to_insert": rows,
            "template_document_id": self.template_document_id,
            "historical_document_id": self.historical_document_id,
            "current_source_document_ids": list(self.current_source_document_ids),
            "requires_approval": True,
            "approved": bool(self.manifest.approved_by),
            "created_at": self.created_at,
        }


class RollForwardPlanStore:
    """Process-local registry of governed plans, keyed by (session, user)."""

    _plans: Dict[Tuple[str, str], GovernedPlan] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, plan: GovernedPlan) -> GovernedPlan:
        with cls._lock:
            cls._plans[(plan.session_id, plan.user_id)] = plan
        return plan

    @classmethod
    def get(cls, session_id: str, user_id: str = "anonymous") -> Optional[GovernedPlan]:
        with cls._lock:
            return cls._plans.get((session_id, user_id))

    @classmethod
    def clear(cls, session_id: Optional[str] = None,
              user_id: str = "anonymous") -> None:
        with cls._lock:
            if session_id is None:
                cls._plans.clear()
            else:
                cls._plans.pop((session_id, user_id), None)


class RollForwardApprovalService:
    """The only path from an approved plan to a governed execution."""

    @classmethod
    def approve_and_execute(cls, session_id: str, approver: str,
                            user_id: str = "anonymous",
                            plan_id: Optional[str] = None) -> Tuple[Any, GovernedPlan]:
        """Approve the governed plan and run it through the real orchestrator.

        Refuses — never simulates — when there is no plan, when the plan no
        longer describes the workflow's documents, or when readiness has since
        regressed. The orchestrator is what mutates; this method only authorises.
        """
        from applications.agent.rollforward_agent import (
            RollForwardAgentHandler,
            RollForwardStage,
        )
        from applications.rollforward.orchestrator import (
            ExecutionRequest,
            RollForwardOrchestrator,
        )
        from applications.rollforward.state_machine import RollForwardStateMachine

        if not approver:
            raise RollForwardApprovalError(
                "An approver is required: execution is authorised by a person, not a request.")

        plan = RollForwardPlanStore.get(session_id, user_id=user_id)
        if plan is None:
            raise RollForwardApprovalError(
                "There is no governed roll-forward plan for this session to approve.")
        if plan_id and plan.plan_id != plan_id:
            raise RollForwardApprovalError(
                "The approved plan is not the plan currently held for this session.")

        assessment = RollForwardAgentHandler.assess(session_id, user_id=user_id)
        if assessment is None:
            raise RollForwardApprovalError("This session has no roll-forward workflow.")
        if assessment.stage != RollForwardStage.PLAN_READY:
            blockers = "; ".join(b.detail for b in assessment.blockers) or "readiness regressed"
            raise RollForwardApprovalError(
                f"The roll-forward is not executable: {blockers}")

        # Approval is recorded on the manifest through the governed state
        # machine, which is what binds the approver to this exact version.
        if plan.manifest.status != ManifestStatus.APPROVED:
            plan.manifest = RollForwardStateMachine.approve(plan.manifest, approver)

        request = ExecutionRequest(
            manifest=plan.manifest,
            mutation_plan=plan.mutation_plan,
            template_path=plan.template_path,
            output_path=plan.output_path,
            source_paths=list(plan.source_paths),
            expected_source_hashes=dict(plan.expected_source_hashes),
            expected_template_hash=plan.expected_template_hash,
            expected_approver=approver,
            actor_id=approver,
        )
        report = RollForwardOrchestrator.execute(request)
        return report, plan


__all__ = [
    "GovernedPlan",
    "RollForwardPlanStore",
    "RollForwardApprovalService",
    "RollForwardApprovalError",
]

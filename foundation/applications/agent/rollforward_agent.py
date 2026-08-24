"""
Roll-Forward Agent handler (Phase PROD-RF-1)
============================================
Location: foundation/applications/agent/rollforward_agent.py

The readiness-first flow behind the deterministic `roll_forward` intent.

Order of authority
------------------
    1. workflow repository       — which document holds which role
    2. deterministic readiness   — what the evidence actually supports
    3. governed manifest + plan  — what may be mutated, and where each value comes from
    4. explicit human approval   — the only thing that authorises execution
    5. RollForwardOrchestrator   — the only thing that produces a result
    6. the selected model        — explanation only, and only of state 1-5

The model appears exactly once, at the end, and only to phrase what the layers
above already decided. It never decides readiness, never selects a source cell,
never chooses what to mutate, and can never mark anything completed.

The rule this module exists to enforce
--------------------------------------
    No governed execution → no "completed".

A response may say a roll-forward is DONE only when a real
RollForwardExecutionReport exists, carrying an execution_id, an output document
with its hash, a publication state, a reconciliation digest, a validation
summary and lineage. Anything else says, plainly, that it did not run — and why.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from applications.agent.models import (
    AgentResponse,
    AgentStep,
    RollForwardResult,
)
from applications.rollforward.workflow_intake import (
    SLOT_ORDER,
    DomainStatus,
    SlotId,
    SlotReadinessStatus,
    SlotValidationStatus,
    WorkflowIntakeSession,
)


class RollForwardStage(str, Enum):
    """Where a roll-forward request got to. Never a claim beyond the facts."""
    BLOCKED = "BLOCKED"                    # inputs or evidence insufficient
    PLAN_UNAVAILABLE = "PLAN_UNAVAILABLE"  # inputs fine, no governed plan for them
    PLAN_READY = "PLAN_READY"              # a governed plan exists, awaiting approval
    EXECUTED = "EXECUTED"                  # a governed execution produced an output


@dataclass
class Blocker:
    """One deterministic reason the roll-forward cannot proceed."""
    code: str
    subject: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "subject": self.subject, "detail": self.detail}


@dataclass
class RollForwardAssessment:
    """The deterministic answer to "can this roll-forward run?".

    Everything in it is read from workflow state. No model contributed to it, so
    it is identical on every run for the same inputs.
    """
    stage: RollForwardStage
    workflow_id: str
    session_id: str
    historical_document_id: Optional[str] = None
    current_source_document_ids: List[str] = field(default_factory=list)
    template_document_id: Optional[str] = None
    periods: Dict[str, Any] = field(default_factory=dict)
    satisfied_inputs: List[str] = field(default_factory=list)
    blockers: List[Blocker] = field(default_factory=list)
    readiness: List[Dict[str, Any]] = field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    timings_ms: Dict[str, float] = field(default_factory=dict)

    @property
    def can_execute(self) -> bool:
        return self.stage == RollForwardStage.PLAN_READY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "workflow": "LOCAL_FILE_ROLL_FORWARD",
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "historical_document_id": self.historical_document_id,
            "current_source_document_ids": list(self.current_source_document_ids),
            "template_document_id": self.template_document_id,
            "periods": dict(self.periods),
            "satisfied_inputs": list(self.satisfied_inputs),
            "blockers": [b.to_dict() for b in self.blockers],
            "readiness": list(self.readiness),
            "plan": self.plan,
            "can_execute": self.can_execute,
            "timings_ms": dict(self.timings_ms),
        }


class _Timer:
    """Stage timings, so "why did that take 18 seconds" is answerable."""

    def __init__(self) -> None:
        self.marks: Dict[str, float] = {}

    def time(self, label: str, fn):
        started = time.perf_counter()
        try:
            return fn()
        finally:
            self.marks[label] = round((time.perf_counter() - started) * 1000, 2)


class RollForwardAgentHandler:
    """Answers a roll-forward request from workflow state alone."""

    # ------------------------------------------------------------------
    # 1-6. READINESS, FROM THE WORKFLOW'S OWN SLOTS
    # ------------------------------------------------------------------

    @classmethod
    def assess(cls, session_id: str, user_id: str = "anonymous") -> Optional[RollForwardAssessment]:
        """Load the workflow and decide, deterministically, what is possible.

        Returns None when the session has no roll-forward intake at all — the
        caller then has nothing workflow-shaped to answer and must not pretend
        otherwise.
        """
        timer = _Timer()
        session = timer.time("load_workflow_ms", lambda: cls._load_session(session_id, user_id))
        if session is None:
            return None

        # Readiness is recomputed here, not read from a cached field, so the
        # answer reflects the evidence as it stands at this moment.
        readiness = timer.time(
            "readiness_ms", lambda: [row.to_dict() for row in session.readiness_summary()])

        assessment = RollForwardAssessment(
            stage=RollForwardStage.BLOCKED,
            workflow_id=session.workflow_id,
            session_id=session.session_id,
            periods=session.periods.to_dict(),
            readiness=readiness,
        )

        cls._collect_input_blockers(session, assessment)
        cls._collect_period_blockers(session, assessment)
        cls._collect_evidence_blockers(readiness, assessment)

        # Slot documents are the ONLY documents a roll-forward may touch. The
        # generic workspace list plays no part: a session can hold any number of
        # unrelated documents and none of them are inputs to this workflow.
        context = session.agent_workflow_context()
        assessment.historical_document_id = context["historical_document_id"]
        assessment.current_source_document_ids = list(context["current_source_document_ids"])
        assessment.template_document_id = context["template_document_id"]

        if assessment.blockers:
            assessment.timings_ms = timer.marks
            return assessment

        plan, plan_blockers = timer.time(
            "plan_ms", lambda: cls._build_plan(session, user_id))
        if plan is None:
            assessment.stage = RollForwardStage.PLAN_UNAVAILABLE
            assessment.blockers.extend(plan_blockers)
        else:
            assessment.stage = RollForwardStage.PLAN_READY
            assessment.plan = plan

        assessment.timings_ms = timer.marks
        return assessment

    @staticmethod
    def _load_session(session_id: str, user_id: str) -> Optional[WorkflowIntakeSession]:
        from adapters.repository import get_repositories

        repos = get_repositories()
        workflow = repos.workflows.get_workflow(session_id, user_id=user_id)
        if workflow is None:
            return None
        assignments = repos.workflows.list_assignments(workflow.workflow_id, user_id=user_id)
        return WorkflowIntakeSession.from_records(workflow, assignments)

    @staticmethod
    def _collect_input_blockers(session: WorkflowIntakeSession,
                                assessment: RollForwardAssessment) -> None:
        for slot_id in SLOT_ORDER:
            state = session.slot(slot_id)
            readiness = state.readiness_status
            if readiness == SlotReadinessStatus.EMPTY:
                assessment.blockers.append(Blocker(
                    "MISSING_INPUT", state.spec.display_name,
                    f"No file has been added to {state.spec.display_name}."))
                continue
            if readiness == SlotReadinessStatus.BLOCKED:
                flagged = next(
                    (a for a in state.assignments
                     if a.validation_status in (SlotValidationStatus.ROLE_MISMATCH,
                                                SlotValidationStatus.FORMAT_REJECTED)), None)
                detail = (f"'{flagged.filename}' does not match this role: "
                          f"{flagged.reasons[0] if flagged.reasons else 'role not confirmed'}"
                          ) if flagged else "The file in this slot could not be confirmed."
                assessment.blockers.append(
                    Blocker("ROLE_NOT_CONFIRMED", state.spec.display_name, detail))
                continue
            assessment.satisfied_inputs.append(state.spec.display_name)

    @staticmethod
    def _collect_period_blockers(session: WorkflowIntakeSession,
                                 assessment: RollForwardAssessment) -> None:
        periods = session.periods
        if periods.historical is None or periods.current is None:
            assessment.blockers.append(Blocker(
                "PERIOD_UNRESOLVED", "Fiscal periods",
                "The periods to roll between could not both be read from the documents."))
        elif not periods.satisfies_invariant:
            assessment.blockers.append(
                Blocker("PERIOD_INVALID", "Fiscal periods", periods.describe()))

    @staticmethod
    def _collect_evidence_blockers(readiness: List[Dict[str, Any]],
                                   assessment: RollForwardAssessment) -> None:
        for row in readiness:
            status = row.get("status")
            if status == DomainStatus.SUPPORTED.value:
                continue
            code = ("MISSING_SOURCE" if status == DomainStatus.MISSING_SOURCE.value
                    else "HUMAN_REVIEW" if status == DomainStatus.HUMAN_REVIEW.value
                    else "UNSUPPORTED_DOMAIN")
            assessment.blockers.append(
                Blocker(code, row["display_name"], row.get("detail", "")))

    # ------------------------------------------------------------------
    # 7. PLAN CONSTRUCTION — governed artifacts only
    # ------------------------------------------------------------------

    @classmethod
    def _build_plan(cls, session: WorkflowIntakeSession,
                    user_id: str) -> Tuple[Optional[Dict[str, Any]], List[Blocker]]:
        """Return the governed plan for these documents, or say why there is none.

        A roll-forward plan is a RollForwardManifest plus a MutationPlan: which
        regions change, which cells they take their values from, how many rows
        are inserted. Both are produced by the planning layer (region profiling
        and source binding) and are bound to the specific documents they were
        built from.

        There is no plan for a session until that planning has run for THESE
        documents. Returning a plausible-looking plan without one would be the
        same defect this module exists to prevent, one layer down: numbers with
        nothing behind them. So this refuses, and names what is missing.
        """
        from applications.agent.rollforward_plan_store import RollForwardPlanStore

        stored = RollForwardPlanStore.get(session.session_id, user_id=user_id)
        if stored is None:
            return None, [Blocker(
                "NO_GOVERNED_PLAN", "Roll-forward plan",
                "No governed roll-forward plan exists for these documents yet. A plan is "
                "produced by the planning layer (region profiling and source binding) and "
                "is bound to the exact files it was built from; none has been produced for "
                "this workflow, so there is nothing approved to execute.")]

        mismatches = stored.binding_mismatches(session)
        if mismatches:
            return None, [Blocker("PLAN_NOT_BOUND", "Roll-forward plan", detail)
                          for detail in mismatches]

        return stored.preview(), []

    # ------------------------------------------------------------------
    # 8-12. THE AGENT-FACING ANSWER
    # ------------------------------------------------------------------

    @classmethod
    def respond(cls, assessment: RollForwardAssessment, run_id: str,
                model_id: str, provider: str,
                steps: Optional[List[AgentStep]] = None) -> AgentResponse:
        """Turn a deterministic assessment into the Agent's answer.

        No model is called on this path. Every sentence below is generated from
        workflow state, which is why it cannot claim a completion that did not
        happen or name a source that was never supplied.
        """
        steps = list(steps or [])
        steps.append(AgentStep(label="Resolved workflow: Local File Roll-Forward", status="done"))
        steps.append(AgentStep(label="Loaded input slots from workflow state", status="done"))
        steps.append(AgentStep(label="Recalculated readiness", status="done"))

        if assessment.stage == RollForwardStage.PLAN_READY:
            steps.append(AgentStep(label="Built governed roll-forward plan", status="done"))
            steps.append(AgentStep(label="Awaiting explicit approval", status="pending"))
        else:
            steps.append(AgentStep(
                label=f"Roll-forward not executable: {len(assessment.blockers)} blocker(s)",
                status="done"))

        return AgentResponse(
            response=cls._render(assessment),
            status="success",
            run_id=run_id,
            intent="roll_forward",
            model_id=model_id,
            provider=provider,
            steps=steps,
            citations=[],
            proposed_actions=[],
            roll_forward_result=None,       # nothing executed, so nothing to report
            roll_forward_assessment=assessment.to_dict(),
        )

    @staticmethod
    def _render(assessment: RollForwardAssessment) -> str:
        """Plain text, assembled from state. Deterministic, never generated."""
        periods = assessment.periods
        span = ""
        if periods.get("historical_period") and periods.get("current_period"):
            span = f" {periods['historical_period']} → {periods['current_period']}"

        if assessment.stage == RollForwardStage.PLAN_READY:
            plan = assessment.plan or {}
            return (
                f"Roll-forward plan{span} is ready for review.\n\n"
                f"Tables to update: {plan.get('tables_to_update', 0)}\n"
                f"Cells to update: {plan.get('cells_to_update', 0)}\n"
                f"Rows to insert: {plan.get('rows_to_insert', 0)}\n\n"
                "Nothing has been changed yet. Approve the plan to execute it."
            )

        lines = [f"Roll-forward cannot execute yet{span}.", ""]
        if assessment.satisfied_inputs:
            lines.append("Present:")
            lines += [f"  ✓ {name}" for name in assessment.satisfied_inputs]
            lines.append("")
        lines.append("Blocked:")
        lines += [f"  ✕ {b.subject} — {b.detail}" for b in assessment.blockers]
        lines.append("")
        lines.append("No document has been modified and no output has been produced.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # RESULT MAPPING — only ever from a real execution report
    # ------------------------------------------------------------------

    @staticmethod
    def result_from_report(report: Any, output_document: Optional[Dict[str, Any]] = None
                           ) -> RollForwardResult:
        """Map a RollForwardExecutionReport onto the Agent's result contract.

        Every field is copied from the report. There is no default that could
        make a failed or partial run look complete: `status` and
        `publication_state` come straight from the orchestrator.
        """
        reconciliation = getattr(report, "reconciliation", None)
        # Counts come from the execution's own structural change records and the
        # reconciliation digest — never from the plan, which is what was intended
        # rather than what happened.
        changes = list(getattr(report, "structural_changes", []) or [])
        rows = sum(getattr(change, "rows_inserted", 0) for change in changes)
        cells = getattr(reconciliation, "total_cells", 0) if reconciliation else 0

        return RollForwardResult(
            execution_id=report.execution_id,
            status=str(getattr(report.status, "value", report.status)),
            publication_state=str(getattr(report.publication_state, "value",
                                          report.publication_state)),
            output_document=output_document,
            output_hash=getattr(report, "output_hash", None),
            regions_changed=len(getattr(report, "executed_regions", []) or []),
            cells_updated=cells,
            rows_inserted=rows,
            reconciliation_status=(
                str(getattr(reconciliation, "overall_status", "NOT_RUN"))
                if reconciliation else "NOT_RUN"),
            reconciliation_detail=(
                f"{reconciliation.matched_cells}/{reconciliation.total_cells} cells matched; "
                f"{reconciliation.mismatched_cells} mismatched, "
                f"{reconciliation.manual_review_items} for manual review"
                if reconciliation else None),
            validation_summary=dict(getattr(report, "validation_summary", {}) or {}),
            lineage_id=getattr(getattr(report, "lineage", None), "lineage_id", None),
            template_preserved=bool(getattr(report, "template_preserved", True)),
            review_available=bool(getattr(report, "output_path", None)),
        )


__all__ = [
    "RollForwardStage",
    "Blocker",
    "RollForwardAssessment",
    "RollForwardAgentHandler",
]

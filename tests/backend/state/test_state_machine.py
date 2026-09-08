from __future__ import annotations

from copy import deepcopy

import pytest

from foundation.domain import (
    AnalysisStatus,
    ApprovedChangeSetStatus,
    DocumentPreflightStatus,
    DocumentStatus,
    ExceptionStatus,
    ExecutionStatus,
    MappingProposalStatus,
    ObjectType,
    SourceAssessmentStatus,
    TaskStatus,
    ValidationStatus,
    ChangeProposalStatus,
)
from foundation.governance.state import (
    AuthenticatedAuthority,
    GuardResult,
    StateTransitionEngine,
    StateTransitionError,
    TransitionContext,
)


EXPECTED = {
    ObjectType.FOUNDATION_TASK: {
        TaskStatus.CREATED: {TaskStatus.ANALYZING, TaskStatus.CANCELLED},
        TaskStatus.ANALYZING: {TaskStatus.AWAITING_REVIEW, TaskStatus.BLOCKED, TaskStatus.FAILED, TaskStatus.CANCELLED},
        TaskStatus.AWAITING_REVIEW: {TaskStatus.READY_FOR_EXECUTION, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.READY_FOR_EXECUTION: {TaskStatus.EXECUTING, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
        TaskStatus.EXECUTING: {TaskStatus.VALIDATING, TaskStatus.BLOCKED, TaskStatus.FAILED},
        TaskStatus.VALIDATING: {TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.FAILED},
        TaskStatus.BLOCKED: {TaskStatus.ANALYZING, TaskStatus.AWAITING_REVIEW, TaskStatus.READY_FOR_EXECUTION, TaskStatus.CANCELLED},
    },
    ObjectType.DOCUMENT_ARTIFACT: {
        DocumentStatus.REGISTERED: {DocumentStatus.PREFLIGHTING, DocumentStatus.REJECTED},
        DocumentStatus.PREFLIGHTING: {DocumentStatus.READY, DocumentStatus.BLOCKED, DocumentStatus.REJECTED},
        DocumentStatus.READY: {DocumentStatus.BLOCKED, DocumentStatus.SUPERSEDED},
        DocumentStatus.BLOCKED: {DocumentStatus.PREFLIGHTING, DocumentStatus.SUPERSEDED, DocumentStatus.REJECTED},
        DocumentStatus.STAGED: {DocumentStatus.RELEASED, DocumentStatus.QUARANTINED},
        DocumentStatus.QUARANTINED: {DocumentStatus.STAGED, DocumentStatus.SUPERSEDED},
        DocumentStatus.RELEASED: {DocumentStatus.QUARANTINED, DocumentStatus.SUPERSEDED},
    },
    ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT: {
        DocumentPreflightStatus.PENDING: {DocumentPreflightStatus.ASSESSING, DocumentPreflightStatus.SUPERSEDED},
        DocumentPreflightStatus.ASSESSING: {DocumentPreflightStatus.COMPLETED, DocumentPreflightStatus.FAILED, DocumentPreflightStatus.SUPERSEDED},
        DocumentPreflightStatus.COMPLETED: {DocumentPreflightStatus.SUPERSEDED},
    },
    ObjectType.SOURCE_ASSESSMENT: {
        SourceAssessmentStatus.PENDING: {SourceAssessmentStatus.ASSESSING, SourceAssessmentStatus.SUPERSEDED},
        SourceAssessmentStatus.ASSESSING: {SourceAssessmentStatus.COMPLETED, SourceAssessmentStatus.FAILED, SourceAssessmentStatus.SUPERSEDED},
        SourceAssessmentStatus.COMPLETED: {SourceAssessmentStatus.SUPERSEDED},
    },
    ObjectType.MAPPING_PROPOSAL: {
        MappingProposalStatus.PROPOSED: {MappingProposalStatus.UNDER_REVIEW, MappingProposalStatus.BLOCKED, MappingProposalStatus.SUPERSEDED},
        MappingProposalStatus.UNDER_REVIEW: {MappingProposalStatus.ACCEPTED, MappingProposalStatus.BLOCKED, MappingProposalStatus.REJECTED, MappingProposalStatus.SUPERSEDED},
        MappingProposalStatus.BLOCKED: {MappingProposalStatus.UNDER_REVIEW, MappingProposalStatus.REJECTED, MappingProposalStatus.SUPERSEDED},
        MappingProposalStatus.ACCEPTED: {MappingProposalStatus.SUPERSEDED},
    },
    ObjectType.CHANGE_PROPOSAL: {
        ChangeProposalStatus.DRAFT: {ChangeProposalStatus.READY_FOR_REVIEW, ChangeProposalStatus.BLOCKED, ChangeProposalStatus.SUPERSEDED},
        ChangeProposalStatus.BLOCKED: {ChangeProposalStatus.READY_FOR_REVIEW, ChangeProposalStatus.SUPERSEDED},
        ChangeProposalStatus.READY_FOR_REVIEW: {ChangeProposalStatus.IN_REVIEW, ChangeProposalStatus.BLOCKED, ChangeProposalStatus.SUPERSEDED},
        ChangeProposalStatus.IN_REVIEW: {ChangeProposalStatus.APPROVED, ChangeProposalStatus.REJECTED, ChangeProposalStatus.BLOCKED, ChangeProposalStatus.SUPERSEDED},
        ChangeProposalStatus.APPROVED: {ChangeProposalStatus.SUPERSEDED},
    },
    ObjectType.APPROVED_CHANGE_SET: {
        ApprovedChangeSetStatus.APPROVED: {ApprovedChangeSetStatus.INVALIDATED, ApprovedChangeSetStatus.REVOKED, ApprovedChangeSetStatus.SUPERSEDED},
    },
    ObjectType.EXECUTION_RESULT: {
        ExecutionStatus.QUEUED: {ExecutionStatus.PREFLIGHTING, ExecutionStatus.CANCELLED},
        ExecutionStatus.PREFLIGHTING: {ExecutionStatus.RUNNING, ExecutionStatus.REFUSED, ExecutionStatus.CANCELLED},
        ExecutionStatus.RUNNING: {ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED},
    },
    ObjectType.VALIDATION_REPORT: {
        ValidationStatus.PENDING: {ValidationStatus.RUNNING, ValidationStatus.CANCELLED},
        ValidationStatus.RUNNING: {ValidationStatus.PASSED, ValidationStatus.FAILED, ValidationStatus.INCONCLUSIVE, ValidationStatus.CANCELLED},
    },
    ObjectType.EXCEPTION_RECORD: {
        ExceptionStatus.OPEN: {ExceptionStatus.ACKNOWLEDGED, ExceptionStatus.REMEDIATION_PENDING},
        ExceptionStatus.ACKNOWLEDGED: {ExceptionStatus.REMEDIATION_PENDING},
        ExceptionStatus.REMEDIATION_PENDING: {ExceptionStatus.RESOLVED, ExceptionStatus.OPEN},
        ExceptionStatus.RESOLVED: {ExceptionStatus.CLOSED, ExceptionStatus.OPEN},
    },
    ObjectType.ANALYSIS_RUN: {
        AnalysisStatus.QUEUED: {AnalysisStatus.RUNNING, AnalysisStatus.CANCELLED},
        AnalysisStatus.RUNNING: {AnalysisStatus.COMPLETED, AnalysisStatus.BLOCKED, AnalysisStatus.FAILED, AnalysisStatus.CANCELLED},
    },
}


class AllowGuard:
    def evaluate(self, record, target_status, context):
        return GuardResult(passed=True, evidence_refs=[], reason="test guard passed")


class DenyGuard:
    def evaluate(self, record, target_status, context):
        return GuardResult(passed=False, evidence_refs=[], reason="required evidence unavailable")


class CaptureAudit:
    def __init__(self):
        self.decisions = []

    def emit(self, decision):
        self.decisions.append(decision)


def _samples(scenarios):
    records = scenarios["C2-02"]["records"] + scenarios["C2-06"]["records"]
    result = {}
    for record in records:
        if record.object_type in EXPECTED and record.object_type not in result:
            result[record.object_type] = record
    assert set(result) == set(EXPECTED)
    return result


def _context(record, request_id="transition-test"):
    return TransitionContext(
        request_id=request_id,
        expected_revision=record.revision,
        authority=AuthenticatedAuthority(
            actor={"actor_type": "SYSTEM", "actor_id": "state-test"},
            authenticated=True,
        ),
        occurred_at="2026-09-08T00:00:00Z",
    )


def test_transition_table_is_exact():
    assert StateTransitionEngine.transitions() == EXPECTED


def test_every_allowed_and_undefined_edge(scenarios):
    engine = StateTransitionEngine()
    for object_type, by_source in EXPECTED.items():
        sample = _samples(scenarios)[object_type]
        enum_type = type(sample.status)
        for source in enum_type:
            allowed = by_source.get(source, set())
            for target in enum_type:
                record = sample.model_copy(update={"status": source})
                if object_type is ObjectType.SOURCE_ASSESSMENT:
                    outcome = sample.outcome if target is SourceAssessmentStatus.COMPLETED else None
                    record = record.model_copy(update={"outcome": outcome})
                audit = CaptureAudit()
                if target in allowed:
                    decision = engine.transition(record, target, _context(record), AllowGuard(), audit)
                    assert decision.next_record.status is target
                    assert decision.next_record.revision == record.revision + 1
                    assert record.status is source
                    assert audit.decisions == [decision]
                else:
                    with pytest.raises(StateTransitionError, match="INVALID_STATE_TRANSITION"):
                        engine.transition(record, target, _context(record), AllowGuard(), audit)
                    assert not audit.decisions


def test_guard_and_revision_fail_closed(scenarios):
    record = _samples(scenarios)[ObjectType.FOUNDATION_TASK].model_copy(update={"status": TaskStatus.AWAITING_REVIEW})
    engine = StateTransitionEngine()
    with pytest.raises(StateTransitionError, match="required evidence unavailable"):
        engine.transition(record, TaskStatus.READY_FOR_EXECUTION, _context(record), DenyGuard(), CaptureAudit())
    bad = _context(record).model_copy(update={"expected_revision": record.revision + 1})
    with pytest.raises(StateTransitionError, match="revision"):
        engine.transition(record, TaskStatus.BLOCKED, bad, AllowGuard(), CaptureAudit())


def test_source_assessment_status_and_outcome_are_separate(scenarios):
    record = _samples(scenarios)[ObjectType.SOURCE_ASSESSMENT].model_copy(
        update={"status": SourceAssessmentStatus.ASSESSING, "outcome": None}
    )
    with pytest.raises(StateTransitionError, match="outcome"):
        StateTransitionEngine().transition(record, SourceAssessmentStatus.COMPLETED, _context(record), AllowGuard(), CaptureAudit())


def test_duplicate_request_returns_prior_decision_without_new_event(scenarios):
    record = _samples(scenarios)[ObjectType.APPROVED_CHANGE_SET]
    audit = CaptureAudit()
    engine = StateTransitionEngine()
    first = engine.transition(record, ApprovedChangeSetStatus.INVALIDATED, _context(record, "same-request"), AllowGuard(), audit)
    duplicate = engine.transition(record, ApprovedChangeSetStatus.INVALIDATED, _context(record, "same-request"), AllowGuard(), audit, prior_decision=first)
    assert duplicate is first
    assert audit.decisions == [first]


def test_scenario_02_partial_task_path_remains_blocked(scenarios):
    task = _samples(scenarios)[ObjectType.FOUNDATION_TASK].model_copy(update={"status": TaskStatus.AWAITING_REVIEW})
    engine = StateTransitionEngine()
    for target in [TaskStatus.BLOCKED, TaskStatus.READY_FOR_EXECUTION, TaskStatus.EXECUTING, TaskStatus.VALIDATING, TaskStatus.BLOCKED]:
        task = engine.transition(task, target, _context(task, f"partial-{target.value}"), AllowGuard(), CaptureAudit()).next_record
    assert task.status is TaskStatus.BLOCKED
    assert task.release_status.value == "WITHHELD"

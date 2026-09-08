"""Exhaustive lifecycle edges from the frozen status model."""

from foundation.domain import (
    AnalysisStatus,
    ApprovedChangeSetStatus,
    ChangeProposalStatus,
    DocumentPreflightStatus,
    DocumentStatus,
    ExceptionStatus,
    ExecutionStatus,
    MappingProposalStatus,
    ObjectType,
    SourceAssessmentStatus,
    TaskStatus,
    ValidationStatus,
)


TRANSITIONS = {
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

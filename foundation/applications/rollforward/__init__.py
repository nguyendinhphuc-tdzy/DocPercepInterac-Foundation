"""
Local File Roll-Forward Domain Package (V1 Contract)
====================================================
Provides formal domain models, manifest specification, lifecycle state machine,
and governance rules for the Transfer Pricing Local File Roll-Forward workflow.

Foundation Core owns structural perception, deterministic bindings, and mutation execution.
Agent owns user intent, plan explanation, and governed proposal presentation.
"""
from __future__ import annotations

from applications.rollforward.models import (
    ManifestStatus,
    RegionClassification,
    SourceBindingStatus,
    SourceType,
    ExecutionGate,
    ValidationRuleType,
    ValidationSeverity,
    DiffChangeType,
    GroundTruthStatus,
    SourceBinding,
    StructuralDelta,
    RowTemplate,
    FigureBinding,
    ValidationRule,
    RollForwardDiff,
    HistoricalReference,
    RollForwardRegion,
    TransitionLog,
    RollForwardManifest,
)
from applications.rollforward.state_machine import (
    RollForwardStateMachine,
    RollForwardStateError,
    IllegalTransitionError,
    UnauthorizedApprovalError,
    ApprovalInvalidationError,
)

__all__ = [
    "ManifestStatus",
    "RegionClassification",
    "SourceBindingStatus",
    "SourceType",
    "ExecutionGate",
    "ValidationRuleType",
    "ValidationSeverity",
    "DiffChangeType",
    "GroundTruthStatus",
    "SourceBinding",
    "StructuralDelta",
    "RowTemplate",
    "FigureBinding",
    "ValidationRule",
    "RollForwardDiff",
    "HistoricalReference",
    "RollForwardRegion",
    "TransitionLog",
    "RollForwardManifest",
    "RollForwardStateMachine",
    "RollForwardStateError",
    "IllegalTransitionError",
    "UnauthorizedApprovalError",
    "ApprovalInvalidationError",
    "ExecutionOutcome",
    "CellMutationSpec",
    "RowMutationSpec",
    "TableMutationSpec",
    "MutationPlan",
    "StructuralValidationReport",
    "MutationExecutionResult",
    "FingerprintService",
    "OxmlRowCloner",
    "StructuralValidator",
    "RePerceptionValidator",
    "StructuralWritebackEngine",
]

from applications.rollforward.structural_writeback import (
    ExecutionOutcome,
    CellMutationSpec,
    RowMutationSpec,
    TableMutationSpec,
    MutationPlan,
    StructuralValidationReport,
    MutationExecutionResult,
    FingerprintService,
    OxmlRowCloner,
    StructuralValidator,
    RePerceptionValidator,
    StructuralWritebackEngine,
)

"""Evidence records and deterministic evidence assessments."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import BusinessTargetID, ExactText, TaskOwnedRecord
from .enums import (
    AssessmentMethod,
    CheckOutcome,
    ErrorCode,
    EvidenceCheckKind,
    EvidenceKind,
    EvidencePeriodScope,
    EvidenceStatus,
    ObjectType,
    SourceAuthority,
)
from .refs import (
    ContentRef,
    DocumentVersionRef,
    EvidenceCheckRef,
    EvidenceRecordRef,
    EvaluatorBinding,
    NativeLocatorRef,
    Period,
    SemanticObjectRef,
    SourceAssessmentRef,
)
from .sources import FreshnessEvaluation
from .values import BusinessValue


class EvidenceRecord(TaskOwnedRecord):
    object_type: Literal[ObjectType.EVIDENCE_RECORD]
    kind: EvidenceKind
    document_version_ref: DocumentVersionRef
    semantic_object_ref: SemanticObjectRef | None = None
    native_locator_ref: NativeLocatorRef | None = None
    content_ref: ContentRef
    observed_value: BusinessValue | None
    formula_text: ExactText | None = None
    authority: SourceAuthority
    period_scope: EvidencePeriodScope
    period: Period | None

    @model_validator(mode="after")
    def period_matches_scope(self) -> "EvidenceRecord":
        if self.period_scope is EvidencePeriodScope.SPECIFIC_PERIOD and self.period is None:
            raise ValueError("SPECIFIC_PERIOD evidence requires period")
        if self.period_scope is EvidencePeriodScope.PERIOD_INDEPENDENT and self.period is not None:
            raise ValueError("PERIOD_INDEPENDENT evidence cannot carry period")
        return self


class EvidenceCheck(TaskOwnedRecord):
    object_type: Literal[ObjectType.EVIDENCE_CHECK]
    check_kind: EvidenceCheckKind
    business_target_id: BusinessTargetID
    source_assessment_refs: list[SourceAssessmentRef]
    evidence_refs: list[EvidenceRecordRef]
    policy_ref: ContentRef
    evaluator_binding: EvaluatorBinding
    method: Literal[AssessmentMethod.DETERMINISTIC]
    outcome: CheckOutcome
    freshness_evaluation: FreshnessEvaluation | None = None
    error_codes: list[ErrorCode]


class EvidenceAssessment(TaskOwnedRecord):
    object_type: Literal[ObjectType.EVIDENCE_ASSESSMENT]
    business_target_id: BusinessTargetID
    source_assessment_refs: list[SourceAssessmentRef]
    evidence_check_refs: list[EvidenceCheckRef]
    evaluator_binding: EvaluatorBinding
    status: EvidenceStatus
    method: Literal[AssessmentMethod.DETERMINISTIC]
    error_codes: list[ErrorCode]

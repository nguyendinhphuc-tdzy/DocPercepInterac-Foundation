"""Reusable source requirements and task-specific source assessments."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import Bool, BusinessTargetID, EvaluatorKey, RecordBase, StrictModel, TaskOwnedRecord, Text, Timestamp
from .enums import (
    AssessmentMethod,
    DocumentRole,
    ErrorCode,
    FreshnessOutcome,
    ObjectType,
    PeriodPolicy,
    SourceAssessmentStatus,
    SourceAuthority,
    SourceSufficiencyOutcome,
)
from .refs import (
    ContentRef,
    DocumentVersionRef,
    EvidenceRecordRef,
    EvaluatorBinding,
    FreshnessPolicyRef,
    Period,
    Ref,
    SourceRequirementRef,
)


class FreshnessEvaluation(StrictModel):
    freshness_policy_ref: FreshnessPolicyRef
    document_version_refs: list[DocumentVersionRef]
    as_of: Timestamp
    input_refs: list[ContentRef]
    evaluator_key: EvaluatorKey
    evaluator_version: Text
    outcome: FreshnessOutcome
    valid_until: Timestamp | None
    reason: Text
    error_codes: list[ErrorCode]


class FreshnessPolicy(RecordBase):
    object_type: Literal[ObjectType.FRESHNESS_POLICY]
    name: Text
    evaluator_key: EvaluatorKey
    policy_ref: ContentRef
    configuration_ref: ContentRef
    required_input_keys: list[Text]
    description: Text


class SourceRequirement(RecordBase):
    object_type: Literal[ObjectType.SOURCE_REQUIREMENT]
    business_target_id: BusinessTargetID
    period_policy: PeriodPolicy
    specific_period: Period | None = None
    freshness_policy_ref: FreshnessPolicyRef
    required_fields: list[Text]
    permitted_roles: list[DocumentRole]
    required_authority: SourceAuthority
    blocking: Bool
    policy_ref: ContentRef

    @model_validator(mode="after")
    def specific_period_matches_policy(self) -> "SourceRequirement":
        if self.period_policy is PeriodPolicy.SPECIFIC_PERIOD and self.specific_period is None:
            raise ValueError("SPECIFIC_PERIOD policy requires specific_period")
        if self.period_policy is not PeriodPolicy.SPECIFIC_PERIOD and self.specific_period is not None:
            raise ValueError("specific_period is only valid for SPECIFIC_PERIOD policy")
        return self


class SourceAssessment(TaskOwnedRecord):
    object_type: Literal[ObjectType.SOURCE_ASSESSMENT]
    source_requirement_ref: SourceRequirementRef
    business_target_id: BusinessTargetID
    document_version_refs: list[DocumentVersionRef]
    outcome: SourceSufficiencyOutcome | None
    resolved_task_period: Period
    resolved_source_period: Period | None
    freshness_policy_ref: FreshnessPolicyRef
    freshness_evaluation: FreshnessEvaluation | None
    evaluator_binding: EvaluatorBinding
    status: SourceAssessmentStatus
    method: Literal[AssessmentMethod.DETERMINISTIC]
    authority: SourceAuthority
    satisfied_fields: list[Text]
    missing_fields: list[Text]
    evidence_refs: list[EvidenceRecordRef]
    error_codes: list[ErrorCode]

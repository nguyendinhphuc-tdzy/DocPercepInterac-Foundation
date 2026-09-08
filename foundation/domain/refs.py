"""Pinned references and shared identity values."""

from __future__ import annotations

from typing import Annotated, TypeAlias

from pydantic import AfterValidator, model_validator

from .base import ExactText, ID, LocalDate, PositiveInt, SHA256, Text, URI, StrictModel
from .enums import ActorType, ObjectType


class ContentRef(StrictModel):
    uri: URI
    sha256: SHA256
    media_type: Text


class DocumentVersionRef(StrictModel):
    document_id: ID
    version_id: ID
    binary_hash: SHA256


class Ref(StrictModel):
    object_type: ObjectType
    object_id: ID
    revision: PositiveInt


Reference = Ref


def _object_type(expected: ObjectType) -> AfterValidator:
    def validate(value: Ref) -> Ref:
        if value.object_type is not expected:
            raise ValueError(f"reference must target {expected.value}")
        return value

    return AfterValidator(validate)


FoundationTaskRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.FOUNDATION_TASK)]
DocumentArtifactRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.DOCUMENT_ARTIFACT)]
DocumentPreflightAssessmentRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT)]
PerceptionSnapshotRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.PERCEPTION_SNAPSHOT)]
SemanticObjectRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.SEMANTIC_OBJECT)]
NativeLocatorRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.NATIVE_LOCATOR)]
NativeBindingRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.NATIVE_BINDING)]
TargetContractDefinitionRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.TARGET_CONTRACT_DEFINITION)]
TargetRegionDefinitionRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.TARGET_REGION_DEFINITION)]
TargetContractInstanceRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.TARGET_CONTRACT_INSTANCE)]
TargetRegionRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.TARGET_REGION)]
RulePackRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.RULE_PACK)]
BusinessRuleRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.BUSINESS_RULE)]
RuleEvaluationRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.RULE_EVALUATION)]
FreshnessPolicyRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.FRESHNESS_POLICY)]
SourceRequirementRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.SOURCE_REQUIREMENT)]
SourceAssessmentRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.SOURCE_ASSESSMENT)]
EvidenceRecordRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.EVIDENCE_RECORD)]
EvidenceCheckRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.EVIDENCE_CHECK)]
EvidenceAssessmentRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.EVIDENCE_ASSESSMENT)]
MappingProposalRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.MAPPING_PROPOSAL)]
AIInteractionRecordRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.AI_INTERACTION_RECORD)]
ChangeProposalRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.CHANGE_PROPOSAL)]
ReviewDecisionRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.REVIEW_DECISION)]
ApprovedChangeSetRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.APPROVED_CHANGE_SET)]
ExecutionResultRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.EXECUTION_RESULT)]
ChangeExecutionResultRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.CHANGE_EXECUTION_RESULT)]
ValidationPlanRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.VALIDATION_PLAN)]
ValidationReportRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.VALIDATION_REPORT)]
ValidationCheckResultRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.VALIDATION_CHECK_RESULT)]
ExceptionRecordRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.EXCEPTION_RECORD)]
AnalysisRunRef: TypeAlias = Annotated[Ref, _object_type(ObjectType.ANALYSIS_RUN)]


class Actor(StrictModel):
    actor_type: ActorType
    actor_id: ID


class Period(StrictModel):
    label: ExactText
    start_date: LocalDate
    end_date: LocalDate

    @model_validator(mode="after")
    def validate_period(self) -> "Period":
        from datetime import date

        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)
        if start > end:
            raise ValueError("period start_date must not follow end_date")
        return self


class EvaluatorBinding(StrictModel):
    evaluator_key: ID
    evaluator_version: Text
    configuration_ref: ContentRef


class SemanticReference(StrictModel):
    snapshot_ref: PerceptionSnapshotRef
    semantic_id: Text

"""Immutable audit event and closed metadata contracts."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from .base import BusinessTargetID, ID, PositiveInt, SHA256, StrictModel, Text, Timestamp
from .enums import (
    AuditMetadataKind,
    BindingStatus,
    ErrorCode,
    EventType,
)
from .refs import (
    AIInteractionRecordRef,
    Actor,
    AnalysisRunRef,
    ApprovedChangeSetRef,
    ContentRef,
    DocumentVersionRef,
    EvaluatorBinding,
    ExceptionRecordRef,
    ExecutionResultRef,
    NativeBindingRef,
    PerceptionSnapshotRef,
    Ref,
    ValidationReportRef,
)


class GovernanceMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.GOVERNANCE]
    summary: Text
    prior_status: str | None
    resulting_status: str | None
    decision_ref: Ref | None = None
    first_material_failure_event_id: ID | None = None


class PerceptionMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.PERCEPTION]
    summary: Text
    analysis_run_ref: AnalysisRunRef
    engine: Text
    engine_version: Text
    configuration_ref: ContentRef
    observation_refs: Annotated[list[ContentRef], Field(min_length=1)]
    perception_snapshot_ref: PerceptionSnapshotRef | None = None
    first_material_failure_event_id: ID | None = None


class NativeBindingMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.NATIVE_BINDING]
    summary: Text
    native_binding_ref: NativeBindingRef
    evaluator_binding: EvaluatorBinding
    observation_refs: Annotated[list[ContentRef], Field(min_length=1)]
    outcome: BindingStatus
    first_material_failure_event_id: ID | None = None


class DeterministicEvaluationMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.DETERMINISTIC_EVALUATION]
    summary: Text
    evaluation_ref: Ref
    evaluator_binding: EvaluatorBinding
    outcome: Text
    first_material_failure_event_id: ID | None = None


class AIInteractionMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.AI_INTERACTION]
    summary: Text
    ai_interaction_ref: AIInteractionRecordRef
    provider: Text
    model: Text
    model_version: Text | None
    instruction_ref: ContentRef
    context_refs: Annotated[list[ContentRef], Field(min_length=1)]
    output_ref: ContentRef


class ReplayMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.REPLAY]
    summary: Text
    approved_change_set_ref: ApprovedChangeSetRef
    execution_ref: ExecutionResultRef | None = None
    engine: Text
    engine_version: Text
    input_document_version_ref: DocumentVersionRef
    output_document_version_ref: DocumentVersionRef | None
    first_material_failure_event_id: ID | None = None


class ValidationMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.VALIDATION]
    summary: Text
    validation_report_ref: ValidationReportRef
    validator: Actor
    validator_version: Text
    configuration_ref: ContentRef
    input_document_version_ref: DocumentVersionRef
    output_document_version_ref: DocumentVersionRef
    observation_refs: Annotated[list[ContentRef], Field(min_length=1)]
    first_material_failure_event_id: ID | None = None


class ExceptionMetadata(StrictModel):
    metadata_kind: Literal[AuditMetadataKind.EXCEPTION]
    summary: Text
    exception_ref: ExceptionRecordRef
    first_material_failure_event_id: ID
    remediation_refs: list[Ref]


AuditMetadata: TypeAlias = Annotated[
    GovernanceMetadata
    | PerceptionMetadata
    | NativeBindingMetadata
    | DeterministicEvaluationMetadata
    | AIInteractionMetadata
    | ReplayMetadata
    | ValidationMetadata
    | ExceptionMetadata,
    Field(discriminator="metadata_kind"),
]


class AuditEvent(StrictModel):
    event_id: ID
    event_version: PositiveInt
    schema_version: Literal["0.1.0"]
    event_type: EventType
    occurred_at: Timestamp
    actor: Actor
    task_id: ID
    correlation_id: ID
    causation_event_id: ID | None
    document_version_refs: list[DocumentVersionRef]
    business_target_ids: list[BusinessTargetID]
    object_refs: list[Ref]
    input_refs: list[Ref]
    output_refs: list[Ref]
    error_codes: list[ErrorCode]
    metadata: AuditMetadata
    integrity_payload_hash: SHA256

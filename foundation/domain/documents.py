"""Task, document identity, preflight, and analysis contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import (
    BusinessTargetID,
    ID,
    NonNegativeInt,
    RecordBase,
    SHA256,
    StrictModel,
    TaskOwnedRecord,
    Text,
    Timestamp,
)
from .enums import (
    AnalysisStatus,
    CapabilityStatus,
    ConformanceClass,
    DocumentFormat,
    DocumentPreflightStatus,
    DocumentRole,
    DocumentStatus,
    ErrorCode,
    LocatorType,
    MutationOperation,
    ObjectType,
    ReleaseStatus,
    TaskStatus,
)
from .refs import (
    Actor,
    ContentRef,
    DocumentArtifactRef,
    DocumentPreflightAssessmentRef,
    DocumentVersionRef,
    ExceptionRecordRef,
    NativeLocatorRef,
    Period,
    Ref,
    RulePackRef,
    TargetContractDefinitionRef,
    TargetContractInstanceRef,
)


class FoundationTask(RecordBase):
    object_type: Literal[ObjectType.FOUNDATION_TASK]
    title: Text
    business_case: Text
    current_period: Period
    status: TaskStatus
    document_refs: list[DocumentArtifactRef]
    target_contract_definition_ref: TargetContractDefinitionRef | None = None
    target_contract_instance_ref: TargetContractInstanceRef | None = None
    rule_pack_ref: RulePackRef | None = None
    required_business_target_ids: list[BusinessTargetID]
    exception_refs: list[ExceptionRecordRef]
    release_status: ReleaseStatus
    prior_period: Period | None = None


class DocumentArtifact(TaskOwnedRecord):
    object_type: Literal[ObjectType.DOCUMENT_ARTIFACT]
    file_name: Text
    role: DocumentRole
    status: DocumentStatus
    version_refs: list[DocumentVersionRef]
    current_version_ref: DocumentVersionRef

    @model_validator(mode="after")
    def current_version_is_registered(self) -> "DocumentArtifact":
        if self.current_version_ref not in self.version_refs:
            raise ValueError("current_version_ref must appear in version_refs")
        return self


class DocumentVersion(TaskOwnedRecord):
    object_type: Literal[ObjectType.DOCUMENT_VERSION]
    revision: Literal[1]
    document_id: ID
    binary_hash: SHA256
    byte_length: NonNegativeInt
    content_ref: ContentRef
    derived_from: DocumentVersionRef | None = None

    @model_validator(mode="after")
    def content_hash_matches_binary_hash(self) -> "DocumentVersion":
        if self.content_ref.sha256 != self.binary_hash:
            raise ValueError("content_ref.sha256 must equal binary_hash")
        return self


class PreflightFinding(StrictModel):
    """Inline preflight observation; intentionally has no record envelope."""

    finding_id: ID
    native_object_type: Text
    part_uri: str | None
    native_locator_refs: list[NativeLocatorRef]
    observation_ref: ContentRef
    description: Text


class CapabilityResult(StrictModel):
    """Inline operation-specific capability result."""

    capability_result_id: ID
    operation: MutationOperation
    native_structure: LocatorType
    document_version_ref: DocumentVersionRef
    native_locator_refs: list[NativeLocatorRef]
    engine: Text
    engine_version: Text
    conformance: ConformanceClass
    qualification_evidence_refs: list[ContentRef]
    status: CapabilityStatus
    reason: Text

    @model_validator(mode="after")
    def supported_capability_has_qualification(self) -> "CapabilityResult":
        if self.status is CapabilityStatus.SUPPORTED:
            if not self.native_locator_refs:
                raise ValueError("SUPPORTED capability requires native locators")
            if not self.qualification_evidence_refs:
                raise ValueError("SUPPORTED capability requires qualification evidence")
            if self.conformance is not ConformanceClass.TRANSITIONAL:
                raise ValueError("only Transitional mutation is qualified in v0.1")
        return self


class DocumentPreflightAssessment(TaskOwnedRecord):
    object_type: Literal[ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT]
    document_version_ref: DocumentVersionRef
    status: DocumentPreflightStatus
    detected_format: DocumentFormat | None
    detected_conformance: ConformanceClass
    format_observation_refs: list[ContentRef]
    protection_findings: list[PreflightFinding]
    native_structure_findings: list[PreflightFinding]
    capability_results: list[CapabilityResult]
    assessor: Actor
    engine: Text
    engine_version: Text
    configuration_ref: ContentRef
    assessed_at: Timestamp | None
    error_codes: list[ErrorCode]
    supersedes_assessment_ref: DocumentPreflightAssessmentRef | None = None

    @model_validator(mode="after")
    def capabilities_belong_to_assessed_version(self) -> "DocumentPreflightAssessment":
        ids = [item.capability_result_id for item in self.capability_results]
        if len(ids) != len(set(ids)):
            raise ValueError("capability_result_id must be unique within an assessment")
        if any(
            item.document_version_ref != self.document_version_ref
            for item in self.capability_results
        ):
            raise ValueError("capability result document version must match assessment")
        return self


class AnalysisRun(TaskOwnedRecord):
    object_type: Literal[ObjectType.ANALYSIS_RUN]
    document_version_refs: list[DocumentVersionRef]
    target_contract_definition_ref: TargetContractDefinitionRef
    target_contract_instance_ref: TargetContractInstanceRef
    rule_pack_ref: RulePackRef
    status: AnalysisStatus
    output_refs: list[Ref]
    error_codes: list[ErrorCode]

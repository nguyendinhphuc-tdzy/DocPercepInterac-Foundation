"""Sealed inline authorization content and authorization records."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import BusinessTargetID, ID, SHA256, StrictModel, TaskOwnedRecord
from .enums import (
    ApprovedChangeSetStatus,
    MutationOperation,
    MutationPayloadType,
    ObjectType,
)
from .refs import (
    ChangeProposalRef,
    ContentRef,
    DocumentVersionRef,
    EvidenceAssessmentRef,
    EvidenceRecordRef,
    NativeLocatorRef,
    ReviewDecisionRef,
    RulePackRef,
    SourceAssessmentRef,
    TargetContractDefinitionRef,
    TargetContractInstanceRef,
    ValidationPlanRef,
)
from .values import Condition, MutationPayload, ProtectedScope


class ApprovedChange(StrictModel):
    approved_change_id: ID
    business_target_id: BusinessTargetID
    change_proposal_ref: ChangeProposalRef
    native_locator_ref: NativeLocatorRef
    operation: MutationOperation
    payload: MutationPayload
    evidence_refs: Annotated[list[EvidenceRecordRef], Field(min_length=1)]
    review_decision_ref: ReviewDecisionRef
    preconditions: Annotated[list[Condition], Field(min_length=1)]
    postconditions: Annotated[list[Condition], Field(min_length=1)]

    @model_validator(mode="after")
    def payload_matches_operation(self) -> "ApprovedChange":
        expected = {
            MutationOperation.REPLACE_RUN_TEXT: MutationPayloadType.RUN_TEXT_REPLACEMENT,
            MutationOperation.REPLACE_SDT_TEXT: MutationPayloadType.SDT_TEXT_REPLACEMENT,
            MutationOperation.REPLACE_SIMPLE_TABLE_CELL_TEXT:
                MutationPayloadType.SIMPLE_TABLE_CELL_TEXT_REPLACEMENT,
        }[self.operation]
        if self.payload.kind is not expected:
            raise ValueError("payload kind must match operation")
        return self


class AuthorizationBinding(StrictModel):
    target_document_version_ref: DocumentVersionRef
    source_document_version_refs: Annotated[
        list[DocumentVersionRef], Field(min_length=1)
    ]
    target_contract_definition_ref: TargetContractDefinitionRef
    target_contract_instance_ref: TargetContractInstanceRef
    rule_pack_ref: RulePackRef
    source_assessment_refs: Annotated[list[SourceAssessmentRef], Field(min_length=1)]
    evidence_assessment_refs: Annotated[list[EvidenceAssessmentRef], Field(min_length=1)]
    review_decision_refs: Annotated[list[ReviewDecisionRef], Field(min_length=1)]
    approved_changes: Annotated[list[ApprovedChange], Field(min_length=1)]
    preconditions: Annotated[list[Condition], Field(min_length=1)]
    postconditions: Annotated[list[Condition], Field(min_length=1)]
    protected_scope: ProtectedScope
    validation_plan_ref: ValidationPlanRef
    mutation_profile: Literal["TRANSITIONAL"]
    qualification_refs: Annotated[list[ContentRef], Field(min_length=1)]

    @model_validator(mode="after")
    def inline_change_ids_are_unique(self) -> "AuthorizationBinding":
        identifiers = [change.approved_change_id for change in self.approved_changes]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("approved_change_id must be unique within authorization")
        if self.protected_scope.document_version_ref != self.target_document_version_ref:
            raise ValueError("protected scope must bind the authorization target version")
        return self


class ApprovedChangeSet(TaskOwnedRecord):
    object_type: Literal[ObjectType.APPROVED_CHANGE_SET]
    status: ApprovedChangeSetStatus
    authorization: AuthorizationBinding
    authorization_digest: SHA256

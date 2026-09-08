"""AI interaction, mapping, and non-authoritative change proposals."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import Bool, BusinessTargetID, TaskOwnedRecord, Text
from .enums import (
    ActorType,
    ChangeProposalStatus,
    ErrorCode,
    MappingProposalStatus,
    MutationOperation,
    MutationPayloadType,
    ObjectType,
)
from .refs import (
    AIInteractionRecordRef,
    Actor,
    ContentRef,
    DocumentVersionRef,
    EvidenceAssessmentRef,
    EvidenceRecordRef,
    MappingProposalRef,
    NativeLocatorRef,
    Ref,
    RuleEvaluationRef,
    RulePackRef,
    SourceAssessmentRef,
    TargetContractDefinitionRef,
    TargetContractInstanceRef,
    TargetRegionRef,
)
from .values import BusinessValue, MutationPayload


class AIInteractionRecord(TaskOwnedRecord):
    object_type: Literal[ObjectType.AI_INTERACTION_RECORD]
    actor: Actor
    provider: Text
    model: Text
    model_version: Text | None
    instruction_ref: ContentRef
    context_refs: list[ContentRef]
    input_refs: list[Ref]
    output_ref: ContentRef
    output_summary: Text
    verification_refs: list[Ref]
    untrusted_content_detected: Bool

    @model_validator(mode="after")
    def actor_is_ai(self) -> "AIInteractionRecord":
        if self.actor.actor_type is not ActorType.AI:
            raise ValueError("AIInteractionRecord actor must have actor_type AI")
        return self


class MappingProposal(TaskOwnedRecord):
    object_type: Literal[ObjectType.MAPPING_PROPOSAL]
    business_target_id: BusinessTargetID
    target_region_ref: TargetRegionRef
    evidence_refs: list[EvidenceRecordRef]
    rule_evaluation_refs: list[RuleEvaluationRef]
    ai_interaction_refs: list[AIInteractionRecordRef]
    proposed_value: BusinessValue
    status: MappingProposalStatus
    rationale: Text
    error_codes: list[ErrorCode]


class ChangeProposal(TaskOwnedRecord):
    object_type: Literal[ObjectType.CHANGE_PROPOSAL]
    status: ChangeProposalStatus
    business_target_id: BusinessTargetID
    target_document_version_ref: DocumentVersionRef
    target_contract_definition_ref: TargetContractDefinitionRef
    target_contract_instance_ref: TargetContractInstanceRef
    rule_pack_ref: RulePackRef
    mapping_proposal_ref: MappingProposalRef
    source_assessment_refs: list[SourceAssessmentRef]
    evidence_assessment_refs: list[EvidenceAssessmentRef]
    proposed_value: BusinessValue
    current_value: BusinessValue
    native_locator_ref: NativeLocatorRef
    operation: MutationOperation
    payload: MutationPayload
    error_codes: list[ErrorCode]

    @model_validator(mode="after")
    def payload_matches_operation(self) -> "ChangeProposal":
        expected = {
            MutationOperation.REPLACE_RUN_TEXT: MutationPayloadType.RUN_TEXT_REPLACEMENT,
            MutationOperation.REPLACE_SDT_TEXT: MutationPayloadType.SDT_TEXT_REPLACEMENT,
            MutationOperation.REPLACE_SIMPLE_TABLE_CELL_TEXT:
                MutationPayloadType.SIMPLE_TABLE_CELL_TEXT_REPLACEMENT,
        }[self.operation]
        if self.payload.kind is not expected:
            raise ValueError("payload kind must match operation")
        return self

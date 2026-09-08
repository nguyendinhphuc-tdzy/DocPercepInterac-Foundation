"""Reusable target definitions and task-specific target bindings."""

from __future__ import annotations

from typing import Literal

from .base import BusinessTargetID, RecordBase, TaskOwnedRecord, Text
from .enums import BusinessValueKind, MutationOperation, ObjectType, TargetVerificationStatus
from .refs import (
    ContentRef,
    DocumentPreflightAssessmentRef,
    DocumentVersionRef,
    NativeBindingRef,
    Ref,
    SemanticObjectRef,
    SourceRequirementRef,
    TargetContractDefinitionRef,
    TargetContractInstanceRef,
    TargetRegionDefinitionRef,
    TargetRegionRef,
    ValidationPlanRef,
)
from .values import CapabilityResultRef, ProtectedScope


class TargetContractDefinition(RecordBase):
    object_type: Literal[ObjectType.TARGET_CONTRACT_DEFINITION]
    name: Text
    business_target_ids: list[BusinessTargetID]
    target_region_definition_refs: list[TargetRegionDefinitionRef]
    source_requirement_refs: list[SourceRequirementRef]
    validation_plan_ref: ValidationPlanRef
    protection_policy_ref: ContentRef


class TargetRegionDefinition(RecordBase):
    object_type: Literal[ObjectType.TARGET_REGION_DEFINITION]
    business_target_id: BusinessTargetID
    description: Text
    allowed_value_kinds: list[BusinessValueKind]
    value_schema_ref: ContentRef
    permitted_operations: list[MutationOperation]
    source_requirement_refs: list[SourceRequirementRef]
    protection_policy_ref: ContentRef


class TargetContractInstance(TaskOwnedRecord):
    object_type: Literal[ObjectType.TARGET_CONTRACT_INSTANCE]
    definition_ref: TargetContractDefinitionRef
    target_document_version_ref: DocumentVersionRef
    target_region_refs: list[TargetRegionRef]
    protected_scope: ProtectedScope
    validation_plan_ref: ValidationPlanRef


class TargetRegion(TaskOwnedRecord):
    object_type: Literal[ObjectType.TARGET_REGION]
    region_definition_ref: TargetRegionDefinitionRef
    target_contract_instance_ref: TargetContractInstanceRef
    business_target_id: BusinessTargetID
    document_version_ref: DocumentVersionRef
    semantic_object_refs: list[SemanticObjectRef]
    native_binding_refs: list[NativeBindingRef]
    verification_status: TargetVerificationStatus
    source_requirement_refs: list[SourceRequirementRef]
    preflight_assessment_refs: list[DocumentPreflightAssessmentRef]
    capability_result_refs: list[CapabilityResultRef]

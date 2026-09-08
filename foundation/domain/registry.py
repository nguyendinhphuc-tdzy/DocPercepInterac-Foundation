"""Canonical ObjectType dispatch for frozen domain records."""

from __future__ import annotations

from collections.abc import Mapping

from .audit import AuditEvent
from .authorization import ApprovedChangeSet
from .base import StrictModel
from .documents import (
    AnalysisRun,
    DocumentArtifact,
    DocumentPreflightAssessment,
    DocumentVersion,
    FoundationTask,
)
from .enums import ObjectType
from .evidence import EvidenceAssessment, EvidenceCheck, EvidenceRecord
from .exceptions import ExceptionRecord
from .execution import ChangeExecutionResult, ExecutionResult
from .perception import NativeBinding, NativeLocator, PerceptionSnapshot, SemanticObject
from .proposals import AIInteractionRecord, ChangeProposal, MappingProposal
from .review import ReviewDecision
from .rules import BusinessRule, RuleEvaluation, RulePack
from .sources import FreshnessPolicy, SourceAssessment, SourceRequirement
from .targets import (
    TargetContractDefinition,
    TargetContractInstance,
    TargetRegion,
    TargetRegionDefinition,
)
from .validation import ValidationCheckResult, ValidationPlan, ValidationReport


DOMAIN_RECORD_MODELS: dict[ObjectType, type[StrictModel]] = {
    ObjectType.FOUNDATION_TASK: FoundationTask,
    ObjectType.DOCUMENT_ARTIFACT: DocumentArtifact,
    ObjectType.DOCUMENT_VERSION: DocumentVersion,
    ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT: DocumentPreflightAssessment,
    ObjectType.PERCEPTION_SNAPSHOT: PerceptionSnapshot,
    ObjectType.SEMANTIC_OBJECT: SemanticObject,
    ObjectType.NATIVE_LOCATOR: NativeLocator,
    ObjectType.NATIVE_BINDING: NativeBinding,
    ObjectType.TARGET_CONTRACT_DEFINITION: TargetContractDefinition,
    ObjectType.TARGET_REGION_DEFINITION: TargetRegionDefinition,
    ObjectType.TARGET_CONTRACT_INSTANCE: TargetContractInstance,
    ObjectType.TARGET_REGION: TargetRegion,
    ObjectType.RULE_PACK: RulePack,
    ObjectType.BUSINESS_RULE: BusinessRule,
    ObjectType.RULE_EVALUATION: RuleEvaluation,
    ObjectType.FRESHNESS_POLICY: FreshnessPolicy,
    ObjectType.SOURCE_REQUIREMENT: SourceRequirement,
    ObjectType.SOURCE_ASSESSMENT: SourceAssessment,
    ObjectType.EVIDENCE_RECORD: EvidenceRecord,
    ObjectType.EVIDENCE_CHECK: EvidenceCheck,
    ObjectType.EVIDENCE_ASSESSMENT: EvidenceAssessment,
    ObjectType.MAPPING_PROPOSAL: MappingProposal,
    ObjectType.AI_INTERACTION_RECORD: AIInteractionRecord,
    ObjectType.CHANGE_PROPOSAL: ChangeProposal,
    ObjectType.REVIEW_DECISION: ReviewDecision,
    ObjectType.APPROVED_CHANGE_SET: ApprovedChangeSet,
    ObjectType.EXECUTION_RESULT: ExecutionResult,
    ObjectType.CHANGE_EXECUTION_RESULT: ChangeExecutionResult,
    ObjectType.VALIDATION_PLAN: ValidationPlan,
    ObjectType.VALIDATION_REPORT: ValidationReport,
    ObjectType.VALIDATION_CHECK_RESULT: ValidationCheckResult,
    ObjectType.EXCEPTION_RECORD: ExceptionRecord,
    ObjectType.ANALYSIS_RUN: AnalysisRun,
    ObjectType.AUDIT_EVENT: AuditEvent,
}


def parse_record(value: Mapping[str, object]) -> StrictModel:
    """Validate one top-level record using its closed ObjectType discriminator."""

    raw_object_type = value.get("object_type")
    try:
        object_type = ObjectType(raw_object_type)
    except (TypeError, ValueError) as error:
        raise ValueError(f"unknown object_type: {raw_object_type!r}") from error
    if object_type is ObjectType.AUDIT_EVENT:
        raise ValueError("AuditEvent uses its dedicated event envelope")
    return DOMAIN_RECORD_MODELS[object_type].model_validate(value)


def parse_audit_event(value: Mapping[str, object]) -> AuditEvent:
    return AuditEvent.model_validate(value)

"""Local File Rule Pack definitions and deterministic evaluations."""

from __future__ import annotations

from typing import Literal

from .base import BusinessTargetID, EvaluatorKey, RecordBase, TaskOwnedRecord, Text
from .enums import CheckOutcome, ErrorCode, ObjectType, RuleType
from .refs import BusinessRuleRef, ContentRef, EvaluatorBinding, Ref, SourceRequirementRef
from .values import BusinessValue


class BusinessRule(RecordBase):
    object_type: Literal[ObjectType.BUSINESS_RULE]
    rule_type: RuleType
    evaluator_key: EvaluatorKey
    business_target_ids: list[BusinessTargetID]
    source_requirement_refs: list[SourceRequirementRef]
    policy_ref: ContentRef
    description: Text


class RuleEvaluation(TaskOwnedRecord):
    object_type: Literal[ObjectType.RULE_EVALUATION]
    business_rule_ref: BusinessRuleRef
    business_target_id: BusinessTargetID
    evaluator_binding: EvaluatorBinding
    input_refs: list[Ref]
    outcome: CheckOutcome
    proposed_value: BusinessValue | None = None
    error_codes: list[ErrorCode]


class RulePack(RecordBase):
    object_type: Literal[ObjectType.RULE_PACK]
    name: Text
    business_rule_refs: list[BusinessRuleRef]
    policy_document_ref: ContentRef

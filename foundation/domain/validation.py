"""Independent validation plans and result records."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .base import Bool, ID, RecordBase, TaskOwnedRecord, Text
from .enums import CheckOutcome, ErrorCode, ObjectType, ValidationCheckKind, ValidationStatus
from .refs import (
    Actor,
    ApprovedChangeSetRef,
    ContentRef,
    DocumentVersionRef,
    ExceptionRecordRef,
    ExecutionResultRef,
    ValidationCheckResultRef,
    ValidationPlanRef,
    ValidationReportRef,
)
from .values import ValidationRequirement


class ValidationPlan(RecordBase):
    object_type: Literal[ObjectType.VALIDATION_PLAN]
    name: Text
    required_checks: Annotated[list[ValidationRequirement], Field(min_length=1)]
    validator_policy_ref: ContentRef
    release_requires_all_targets: Bool


class ValidationCheckResult(TaskOwnedRecord):
    object_type: Literal[ObjectType.VALIDATION_CHECK_RESULT]
    validation_report_ref: ValidationReportRef
    requirement_id: ID
    kind: ValidationCheckKind
    outcome: CheckOutcome
    observation_ref: ContentRef
    error_codes: list[ErrorCode]


class ValidationReport(TaskOwnedRecord):
    object_type: Literal[ObjectType.VALIDATION_REPORT]
    execution_ref: ExecutionResultRef
    approved_change_set_ref: ApprovedChangeSetRef
    validation_plan_ref: ValidationPlanRef
    input_document_version_ref: DocumentVersionRef
    output_document_version_ref: DocumentVersionRef
    validator: Actor
    status: ValidationStatus
    check_result_refs: list[ValidationCheckResultRef]
    blocking_exception_refs: list[ExceptionRecordRef]
    error_codes: list[ErrorCode]

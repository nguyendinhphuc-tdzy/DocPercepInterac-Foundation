"""Replay request boundary and execution result contracts."""

from __future__ import annotations

from typing import Literal

from .base import ID, StrictModel, TaskOwnedRecord, Text
from .enums import ChangeExecutionStatus, ErrorCode, ExecutionStatus, ObjectType
from .refs import ApprovedChangeSetRef, ChangeExecutionResultRef, DocumentVersionRef, ExecutionResultRef
from .values import BusinessValue


class ReplayRequest(StrictModel):
    """Internal replay command; intentionally has no record envelope."""

    execution_id: ID
    approved_change_set_ref: ApprovedChangeSetRef


class ChangeExecutionResult(TaskOwnedRecord):
    object_type: Literal[ObjectType.CHANGE_EXECUTION_RESULT]
    execution_ref: ExecutionResultRef
    approved_change_set_ref: ApprovedChangeSetRef
    approved_change_id: ID
    status: ChangeExecutionStatus
    observed_before: BusinessValue | None = None
    observed_after: BusinessValue | None = None
    error_codes: list[ErrorCode]


class ExecutionResult(TaskOwnedRecord):
    object_type: Literal[ObjectType.EXECUTION_RESULT]
    approved_change_set_ref: ApprovedChangeSetRef
    input_document_version_ref: DocumentVersionRef
    status: ExecutionStatus
    engine: Text
    engine_version: Text
    change_result_refs: list[ChangeExecutionResultRef]
    output_document_version_ref: DocumentVersionRef | None = None
    error_codes: list[ErrorCode]

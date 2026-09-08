"""Governed exception records."""

from __future__ import annotations

from typing import Literal

from .base import BusinessTargetID, TaskOwnedRecord, Text
from .enums import ErrorCode, ExceptionStatus, ObjectType
from .refs import Actor, Ref


class ExceptionRecord(TaskOwnedRecord):
    object_type: Literal[ObjectType.EXCEPTION_RECORD]
    error_code: ErrorCode
    status: ExceptionStatus
    business_target_id: BusinessTargetID | None = None
    related_refs: list[Ref]
    detected_by: Actor
    details: Text
    resolution_refs: list[Ref]

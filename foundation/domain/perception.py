"""Semantic perception and exact native identity contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from .base import ExactText, SHA256, TaskOwnedRecord, Text
from .enums import BindingStatus, LocatorType, ObjectType
from .refs import (
    AnalysisRunRef,
    ContentRef,
    DocumentVersionRef,
    NativeBindingRef,
    NativeLocatorRef,
    Ref,
    SemanticObjectRef,
    SemanticReference,
)
from .values import BusinessValue, NativeAddress


class PerceptionSnapshot(TaskOwnedRecord):
    object_type: Literal[ObjectType.PERCEPTION_SNAPSHOT]
    document_version_ref: DocumentVersionRef
    analysis_run_ref: AnalysisRunRef
    engine: Text
    engine_version: Text
    configuration_ref: ContentRef
    semantic_object_refs: list[SemanticObjectRef]
    limitations: list[ExactText]


class SemanticObject(TaskOwnedRecord):
    object_type: Literal[ObjectType.SEMANTIC_OBJECT]
    semantic_reference: SemanticReference
    object_kind: Text
    value: BusinessValue
    parent_ref: SemanticObjectRef | None = None
    native_binding_refs: list[NativeBindingRef]


class NativeLocator(TaskOwnedRecord):
    object_type: Literal[ObjectType.NATIVE_LOCATOR]
    document_version_ref: DocumentVersionRef
    part_uri: ExactText
    locator_type: LocatorType
    address: NativeAddress
    expected_object_type: Text
    capture_engine: Text
    structural_fingerprint: SHA256
    fingerprint_profile_ref: ContentRef

    @model_validator(mode="after")
    def address_matches_locator_type(self) -> "NativeLocator":
        if self.locator_type is not self.address.kind:
            raise ValueError("locator_type must match address.kind")
        return self


class NativeBinding(TaskOwnedRecord):
    object_type: Literal[ObjectType.NATIVE_BINDING]
    semantic_object_ref: SemanticObjectRef
    native_locator_refs: list[NativeLocatorRef]
    status: BindingStatus
    method: Text
    reason: Text

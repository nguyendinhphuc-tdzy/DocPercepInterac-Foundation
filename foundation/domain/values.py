"""Closed value, native address, condition, and payload unions."""

from __future__ import annotations

import math
from typing import Annotated, Literal, TypeAlias

from pydantic import Field, JsonValue, StrictBool, model_validator

from .base import (
    BusinessTargetID,
    DecimalString,
    ExactText,
    ID,
    IntegerString,
    LocalDate,
    PositiveInt,
    SHA256,
    StrictModel,
    Text,
    URI,
)
from .enums import (
    BusinessValueKind,
    ConditionKind,
    ConditionValueTargetKind,
    ConformanceClass,
    DefinedNameScope,
    LocatorType,
    MutationOperation,
    MutationPayloadType,
    ValidationCheckKind,
    XlsxRangeKind,
)
from .refs import (
    ContentRef,
    DocumentPreflightAssessmentRef,
    DocumentVersionRef,
    EvidenceAssessmentRef,
    NativeLocatorRef,
    Ref,
)


def _assert_finite_json(value: JsonValue) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("structured data numbers must be finite")
    if isinstance(value, list):
        for item in value:
            _assert_finite_json(item)
    elif isinstance(value, dict):
        for item in value.values():
            _assert_finite_json(item)


class TextBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.TEXT]
    review_text: ExactText
    value: ExactText


class DecimalBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.DECIMAL]
    review_text: ExactText
    value: DecimalString


class IntegerBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.INTEGER]
    review_text: ExactText
    value: IntegerString


class DateBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.DATE]
    review_text: ExactText
    value: LocalDate


class BooleanBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.BOOLEAN]
    review_text: ExactText
    value: StrictBool


class CurrencyBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.CURRENCY]
    review_text: ExactText
    amount: DecimalString
    currency_code: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class PercentBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.PERCENT]
    review_text: ExactText
    percentage: DecimalString


class StructuredBusinessValue(StrictModel):
    kind: Literal[BusinessValueKind.STRUCTURED]
    review_text: ExactText
    schema_ref: ContentRef
    value: dict[str, JsonValue]

    @model_validator(mode="after")
    def reject_non_finite_numbers(self) -> "StructuredBusinessValue":
        _assert_finite_json(self.value)
        return self


BusinessValue: TypeAlias = Annotated[
    TextBusinessValue
    | DecimalBusinessValue
    | IntegerBusinessValue
    | DateBusinessValue
    | BooleanBusinessValue
    | CurrencyBusinessValue
    | PercentBusinessValue
    | StructuredBusinessValue,
    Field(discriminator="kind"),
]


class NativeElementSegment(StrictModel):
    namespace_uri: URI
    local_name: ExactText
    ordinal: PositiveInt


NativeElementPath: TypeAlias = Annotated[list[NativeElementSegment], Field(min_length=1)]


class DocxContentControlAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_CONTENT_CONTROL]
    sdt_id: ExactText
    element_path: NativeElementPath


class DocxBookmarkAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_BOOKMARK]
    bookmark_id: ExactText
    bookmark_name: ExactText
    start_path: NativeElementPath
    end_path: NativeElementPath


class DocxParagraphAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_PARAGRAPH]
    paragraph_path: NativeElementPath


class DocxRunAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_RUN]
    run_path: NativeElementPath


class DocxTableCellAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_TABLE_CELL]
    table_path: NativeElementPath
    row_ordinal: PositiveInt
    cell_ordinal: PositiveInt
    cell_path: NativeElementPath


class DocxRelationshipAddress(StrictModel):
    kind: Literal[LocatorType.DOCX_RELATIONSHIP]
    relationship_id: ExactText
    owner_part_uri: ExactText


class XlsxCellAddress(StrictModel):
    kind: Literal[LocatorType.XLSX_CELL]
    sheet_id: ExactText
    cell_address: Annotated[str, Field(pattern=r"^[A-Z]{1,3}[1-9][0-9]*$")]


class XlsxDefinedNameAddress(StrictModel):
    kind: Literal[LocatorType.XLSX_DEFINED_NAME]
    name: ExactText
    scope: DefinedNameScope
    scope_sheet_id: ExactText | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "XlsxDefinedNameAddress":
        if self.scope is DefinedNameScope.WORKSHEET and self.scope_sheet_id is None:
            raise ValueError("worksheet-scoped name requires scope_sheet_id")
        if self.scope is DefinedNameScope.WORKBOOK and self.scope_sheet_id is not None:
            raise ValueError("workbook-scoped name cannot carry scope_sheet_id")
        return self


class XlsxTableRangeAddress(StrictModel):
    kind: Literal[LocatorType.XLSX_TABLE_RANGE]
    range_kind: XlsxRangeKind
    sheet_id: ExactText
    range_address: ExactText
    table_id: ExactText | None = None
    table_part_uri: ExactText | None = None

    @model_validator(mode="after")
    def validate_range_kind(self) -> "XlsxTableRangeAddress":
        table_fields = (self.table_id, self.table_part_uri)
        if self.range_kind is XlsxRangeKind.TABLE and any(v is None for v in table_fields):
            raise ValueError("table address requires table_id and table_part_uri")
        if self.range_kind is XlsxRangeKind.RANGE and any(v is not None for v in table_fields):
            raise ValueError("plain range address cannot carry table identity")
        return self


NativeAddress: TypeAlias = Annotated[
    DocxContentControlAddress
    | DocxBookmarkAddress
    | DocxParagraphAddress
    | DocxRunAddress
    | DocxTableCellAddress
    | DocxRelationshipAddress
    | XlsxCellAddress
    | XlsxDefinedNameAddress
    | XlsxTableRangeAddress,
    Field(discriminator="kind"),
]


class CapabilityResultRef(StrictModel):
    preflight_assessment_ref: DocumentPreflightAssessmentRef
    capability_result_id: ID


class ProtectedScope(StrictModel):
    document_version_ref: DocumentVersionRef
    protected_locator_refs: list[NativeLocatorRef]
    preserve_outside_approved_changes: Literal[True]
    serialization_allowance_ref: ContentRef | None = None


class ValidationRequirement(StrictModel):
    requirement_id: ID
    kind: ValidationCheckKind
    mandatory: StrictBool
    business_target_ids: list[BusinessTargetID]
    description: ExactText


class InputNativeObjectTarget(StrictModel):
    kind: Literal[ConditionValueTargetKind.INPUT_NATIVE_OBJECT]
    native_locator_ref: NativeLocatorRef


class OutputApprovedChangeTarget(StrictModel):
    kind: Literal[ConditionValueTargetKind.OUTPUT_APPROVED_CHANGE]
    approved_change_id: ID


ConditionValueTarget: TypeAlias = Annotated[
    InputNativeObjectTarget | OutputApprovedChangeTarget,
    Field(discriminator="kind"),
]


class BinaryHashEqualsCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.BINARY_HASH_EQUALS]
    document_version_ref: DocumentVersionRef
    expected_binary_hash: SHA256


class TextEqualsCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.TEXT_EQUALS]
    target: ConditionValueTarget
    expected_text: ExactText


class ValueEqualsCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.VALUE_EQUALS]
    target: ConditionValueTarget
    expected_value: BusinessValue
    value_reader_policy_ref: ContentRef


class CapabilitySupportedCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.CAPABILITY_SUPPORTED]
    native_locator_ref: NativeLocatorRef
    capability_result_ref: CapabilityResultRef
    operation: MutationOperation
    engine: Text
    engine_version: Text
    conformance: ConformanceClass


class EvidenceVerifiedCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.EVIDENCE_VERIFIED]
    evidence_assessment_ref: EvidenceAssessmentRef
    business_target_id: BusinessTargetID


class PreserveScopeCondition(StrictModel):
    condition_id: ID
    kind: Literal[ConditionKind.PRESERVE_SCOPE]
    protected_scope: ProtectedScope


Condition: TypeAlias = Annotated[
    BinaryHashEqualsCondition
    | TextEqualsCondition
    | ValueEqualsCondition
    | CapabilitySupportedCondition
    | EvidenceVerifiedCondition
    | PreserveScopeCondition,
    Field(discriminator="kind"),
]


class RunTextReplacementPayload(StrictModel):
    kind: Literal[MutationPayloadType.RUN_TEXT_REPLACEMENT]
    replacement_text: ExactText


class SdtTextReplacementPayload(StrictModel):
    kind: Literal[MutationPayloadType.SDT_TEXT_REPLACEMENT]
    replacement_text: ExactText


class SimpleTableCellTextReplacementPayload(StrictModel):
    kind: Literal[MutationPayloadType.SIMPLE_TABLE_CELL_TEXT_REPLACEMENT]
    replacement_text: ExactText


MutationPayload: TypeAlias = Annotated[
    RunTextReplacementPayload
    | SdtTextReplacementPayload
    | SimpleTableCellTextReplacementPayload,
    Field(discriminator="kind"),
]

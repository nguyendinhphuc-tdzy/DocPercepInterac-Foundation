"""Typed Golden Corpus manifest, observation, and report values."""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator

from foundation.domain import (
    Bool,
    CapabilityStatus,
    ContentRef,
    DocumentFormat,
    ErrorCode,
    ID,
    MutationOperation,
    NonNegativeInt,
    SHA256,
    StrictModel,
    Text,
)


class GoldenCase(StrictModel):
    case_id: ID
    input_document: ContentRef
    input_hash: SHA256
    format: DocumentFormat
    feature_profile: list[Text]
    operation: MutationOperation
    expected_capability: CapabilityStatus
    expected_preservation: list[Text]
    expected_failure: ErrorCode | None
    qualification_scope: Text

    @model_validator(mode="after")
    def input_identity_matches(self) -> "GoldenCase":
        if self.input_hash != self.input_document.sha256:
            raise ValueError("input_hash must match input_document.sha256")
        return self


class GoldenManifest(StrictModel):
    schema_version: Literal["0.1.0"]
    manifest_id: ID
    qualification_claimed: Literal[False]
    cases: list[GoldenCase]


class GoldenObservation(StrictModel):
    case_id: ID
    adapter_id: Text
    adapter_version: Text
    observed_capability: CapabilityStatus
    preservation_observations: list[Text]
    error_code: ErrorCode | None


class GoldenResult(StrictModel):
    case_id: ID
    passed: Bool
    differences: list[Text]
    observation: GoldenObservation


class GoldenReport(StrictModel):
    schema_version: Literal["0.1.0"]
    manifest_id: ID
    qualification_claimed: Literal[False]
    total_cases: NonNegativeInt
    passed_cases: NonNegativeInt
    failed_cases: NonNegativeInt
    overall_result: Literal["PASS", "FAIL"]
    results: list[GoldenResult]

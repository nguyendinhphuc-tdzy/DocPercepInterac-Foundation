"""Structured inputs and outcomes for frozen runtime invariants."""

from __future__ import annotations

from foundation.domain import (
    Bool,
    DocumentVersionRef,
    ErrorCode,
    NativeLocatorRef,
    NonNegativeInt,
    ReplayRequest,
    SHA256,
    StrictModel,
    Text,
    Ref,
)


class LocatorResolutionObservation(StrictModel):
    locator_ref: NativeLocatorRef
    document_version_ref: DocumentVersionRef
    match_count: NonNegativeInt
    observed_structural_fingerprint: SHA256 | None
    exact_address_used: Bool
    fuzzy_fallback_used: Bool


class InvariantContext(StrictModel):
    records: tuple[StrictModel, ...]
    replay_requests: tuple[ReplayRequest, ...] = ()
    locator_observations: tuple[LocatorResolutionObservation, ...] = ()


class InvariantResult(StrictModel):
    invariant_id: Text
    passed: Bool
    error_code: ErrorCode | None
    affected_refs: list[Ref]
    blocking: Bool
    reason: Text

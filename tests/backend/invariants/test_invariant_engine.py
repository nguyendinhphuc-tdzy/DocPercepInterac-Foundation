from __future__ import annotations

from copy import deepcopy

from foundation.domain import ErrorCode, ObjectType
from foundation.governance.invariants import (
    INVARIANT_IDS,
    InvariantContext,
    InvariantEngine,
    LocatorResolutionObservation,
)


REQUIRED_IDS = {
    "FND-INV-DOC-001", "FND-INV-ID-001", "FND-INV-ID-002",
    "FND-INV-LOC-001", "FND-INV-CAP-001", "FND-INV-EVAL-001",
    "FND-INV-SRC-001", "FND-INV-EVD-001", "FND-INV-FRESH-001",
    "FND-INV-AI-001", "FND-INV-AUTH-001", "FND-INV-AUTH-002",
    "FND-INV-AUTH-003", "FND-INV-REPLAY-001", "FND-INV-REL-001",
}


def _positive_context(scenario):
    locators = [r for r in scenario["records"] if r.object_type is ObjectType.NATIVE_LOCATOR]
    observations = tuple(
        LocatorResolutionObservation(
            locator_ref={"object_type": "NativeLocator", "object_id": item.id, "revision": item.revision},
            document_version_ref=item.document_version_ref,
            match_count=1,
            observed_structural_fingerprint=item.structural_fingerprint,
            exact_address_used=True,
            fuzzy_fallback_used=False,
        )
        for item in locators
    )
    return InvariantContext(
        records=scenario["records"],
        replay_requests=scenario["replay_requests"],
        locator_observations=observations,
    )


def test_required_frozen_invariant_ids_are_registered():
    assert REQUIRED_IDS <= INVARIANT_IDS


def test_valid_scenario_passes_all_b0_invariants(scenarios):
    results = InvariantEngine().evaluate_all(_positive_context(scenarios["C2-01"]))
    assert {item.invariant_id for item in results} >= REQUIRED_IDS
    assert all(item.passed for item in results), [item for item in results if not item.passed]


def test_missing_locator_observation_fails_closed(scenarios):
    context = InvariantContext(records=scenarios["C2-01"]["records"], replay_requests=scenarios["C2-01"]["replay_requests"])
    result = InvariantEngine().evaluate("FND-INV-LOC-001", context)
    assert not result.passed and result.blocking
    assert result.error_code is ErrorCode.LOCATOR_NOT_FOUND


def test_fuzzy_or_ambiguous_resolution_never_passes(scenarios):
    context = _positive_context(scenarios["C2-01"])
    observation = context.locator_observations[0]
    ambiguous = context.model_copy(update={"locator_observations": (observation.model_copy(update={"match_count": 2}),)})
    result = InvariantEngine().evaluate("FND-INV-LOC-001", ambiguous)
    assert result.error_code is ErrorCode.LOCATOR_AMBIGUOUS
    fuzzy = context.model_copy(update={"locator_observations": (observation.model_copy(update={"fuzzy_fallback_used": True}),)})
    assert not InvariantEngine().evaluate("FND-INV-LOC-001", fuzzy).passed


def test_tampered_authorization_fails_digest_invariant(scenarios):
    context = _positive_context(scenarios["C2-01"])
    records = list(context.records)
    index = next(i for i, item in enumerate(records) if item.object_type is ObjectType.APPROVED_CHANGE_SET)
    records[index] = records[index].model_copy(update={"authorization_digest": "0" * 64})
    result = InvariantEngine().evaluate("FND-INV-AUTH-002", context.model_copy(update={"records": tuple(records)}))
    assert not result.passed
    assert result.error_code is ErrorCode.APPROVAL_CONTENT_MISMATCH


def test_ai_cannot_supply_authority_when_evidence_is_insufficient(scenarios):
    results = InvariantEngine().evaluate_all(_positive_context(scenarios["C2-05"]))
    by_id = {item.invariant_id: item for item in results}
    assert by_id["FND-INV-AI-001"].passed
    assert by_id["FND-INV-AUTH-001"].passed
    assert not any(r.object_type is ObjectType.APPROVED_CHANGE_SET for r in scenarios["C2-05"]["records"])


def test_partial_success_never_marks_whole_task_releasable(scenarios):
    result = InvariantEngine().evaluate("FND-INV-REL-001", _positive_context(scenarios["C2-02"]))
    assert result.passed

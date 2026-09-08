from __future__ import annotations

import pytest

from foundation.domain import (
    Actor,
    ActorType,
    ChangeProposal,
    ChangeProposalStatus,
    DocumentPreflightAssessment,
    DocumentVersionRef,
    ErrorCode,
    MutationOperation,
    ObjectType,
    Ref,
    ReleaseStatus,
    ReviewOutcome,
    SourceSufficiencyOutcome,
    TargetContractDefinition,
    TargetVerificationStatus,
    TaskStatus,
)
from foundation.governance.invariants import (
    InvariantContext,
    InvariantEngine,
    LocatorResolutionObservation,
)


def _record(records, object_type, object_id, revision=None):
    matches = [
        item
        for item in records
        if item.object_type is object_type
        and item.id == object_id
        and (revision is None or item.revision == revision)
    ]
    assert len(matches) == 1, (object_type, object_id, revision, matches)
    return matches[0]


def _replace(records, replacement):
    return tuple(
        replacement if item.object_type is replacement.object_type and item.id == replacement.id and item.revision == replacement.revision else item
        for item in records
    )


def _context(records):
    observations = tuple(
        LocatorResolutionObservation(
            locator_ref={"object_type": "NativeLocator", "object_id": item.id, "revision": item.revision},
            document_version_ref=item.document_version_ref,
            match_count=1,
            observed_structural_fingerprint=item.structural_fingerprint,
            exact_address_used=True,
            fuzzy_fallback_used=False,
        )
        for item in records
        if item.object_type is ObjectType.NATIVE_LOCATOR
    )
    return InvariantContext(records=tuple(records), locator_observations=observations)


def _engine_result(scenario, invariant_id, records=None):
    return InvariantEngine().evaluate(invariant_id, _context(records or scenario["records"]))


def _change_set(records):
    return _record(records, ObjectType.APPROVED_CHANGE_SET, "changeset-c2-01")


def _with_auth(change_set, **updates):
    authorization = change_set.authorization.model_copy(update=updates)
    return change_set.model_copy(update={"authorization": authorization})


def test_c2_01_source_completeness_remains_valid(scenarios):
    result = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001")
    assert result.passed


def test_blocking_requirement_omitted_fails_closed(scenarios):
    records = scenarios["C2-01"]["records"]
    change_set = _change_set(records)
    change_set = _with_auth(change_set, source_assessment_refs=[])
    result = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", _replace(records, change_set))
    assert result.error_code is ErrorCode.SOURCE_MISSING


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (SourceSufficiencyOutcome.MISSING, ErrorCode.SOURCE_MISSING),
        (SourceSufficiencyOutcome.STALE, ErrorCode.SOURCE_STALE),
    ],
)
def test_blocking_requirement_bad_assessment_fails_closed(scenarios, outcome, expected):
    records = scenarios["C2-01"]["records"]
    assessment = _record(records, ObjectType.SOURCE_ASSESSMENT, "ncp-source-assessment-c2-01")
    assessment = assessment.model_copy(update={"outcome": outcome})
    result = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", _replace(records, assessment))
    assert result.error_code is expected


def test_source_assessment_wrong_target_fails_closed(scenarios):
    records = scenarios["C2-01"]["records"]
    assessment = _record(records, ObjectType.SOURCE_ASSESSMENT, "ncp-source-assessment-c2-01")
    assessment = assessment.model_copy(update={"business_target_id": "VN_LOCAL_FILE.FINANCIAL.OTHER"})
    result = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", _replace(records, assessment))
    assert result.error_code is ErrorCode.SOURCE_MISSING


def test_source_assessment_from_another_task_fails_closed(scenarios):
    records = scenarios["C2-01"]["records"]
    assessment = _record(records, ObjectType.SOURCE_ASSESSMENT, "ncp-source-assessment-c2-01")
    assessment = assessment.model_copy(update={"task_id": "another-task"})
    result = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", _replace(records, assessment))
    assert result.error_code is ErrorCode.SOURCE_MISSING


def test_unresolved_stale_replacement_makes_selected_source_inapplicable(scenarios):
    records = scenarios["C2-01"]["records"]
    assessment = _record(records, ObjectType.SOURCE_ASSESSMENT, "ncp-source-assessment-c2-01")
    replacement = assessment.model_copy(update={
        "id": "ncp-source-assessment-replacement-c2-01",
        "outcome": SourceSufficiencyOutcome.STALE,
    })
    checked = _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", records + (replacement,))
    assert checked.error_code is ErrorCode.SOURCE_STALE


def test_non_blocking_requirement_may_be_absent(scenarios):
    records = scenarios["C2-01"]["records"]
    requirement = _record(records, ObjectType.SOURCE_REQUIREMENT, "ncp-requirement-c2-01")
    optional = requirement.model_copy(update={"id": "optional-requirement-c2-01", "blocking": False})
    definition = _record(records, ObjectType.TARGET_CONTRACT_DEFINITION, "target-contract-c2-01")
    definition = definition.model_copy(update={
        "source_requirement_refs": [
            *definition.source_requirement_refs,
            Ref(object_type=ObjectType.SOURCE_REQUIREMENT, object_id=optional.id, revision=optional.revision),
        ]
    })
    records = _replace(records, definition) + (optional,)
    assert _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", records).passed


def test_c2_02_benchmark_block_remains_partial_and_withheld(scenarios):
    records = scenarios["C2-02"]["records"]
    result = _engine_result(scenarios["C2-02"], "FND-INV-REL-001")
    assert result.passed
    task = _record(records, ObjectType.FOUNDATION_TASK, "task-c2-02", revision=max(item.revision for item in records if item.object_type is ObjectType.FOUNDATION_TASK and item.id == "task-c2-02"))
    assert task.release_status is ReleaseStatus.WITHHELD


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("engine", "python-docx"),
        ("engine_version", "0.8.11"),
        ("conformance", "STRICT"),
    ],
)
def test_capability_condition_tuple_mismatch_fails(scenarios, field, value):
    records = scenarios["C2-01"]["records"]
    change_set = _change_set(records)
    condition = next(item for item in change_set.authorization.preconditions if item.kind.value == "CAPABILITY_SUPPORTED")
    condition = condition.model_copy(update={field: value})
    change_set = _with_auth(change_set, preconditions=[condition, *[item for item in change_set.authorization.preconditions if item is not next(item for item in change_set.authorization.preconditions if item.kind.value == "CAPABILITY_SUPPORTED")]])
    result = _engine_result(scenarios["C2-01"], "FND-INV-CAP-001", _replace(records, change_set))
    assert result.error_code is ErrorCode.EXECUTION_UNSUPPORTED


def test_capability_result_wrong_document_version_fails(scenarios):
    records = scenarios["C2-01"]["records"]
    preflight = _record(records, ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT, "preflight-c2-01")
    result = preflight.capability_results[0].model_copy(update={
        "document_version_ref": DocumentVersionRef(document_id="other-document", version_id="other-version", binary_hash="0" * 64)
    })
    preflight = preflight.model_copy(update={"capability_results": [result]})
    checked = _engine_result(scenarios["C2-01"], "FND-INV-CAP-001", _replace(records, preflight))
    assert checked.error_code is ErrorCode.EXECUTION_UNSUPPORTED


def test_capability_locator_scope_qualification_and_support_are_required(scenarios):
    records = scenarios["C2-01"]["records"]
    preflight = _record(records, ObjectType.DOCUMENT_PREFLIGHT_ASSESSMENT, "preflight-c2-01")
    capability = preflight.capability_results[0]
    for updates in ({"native_locator_refs": []}, {"qualification_evidence_refs": []}, {"status": "UNSUPPORTED"}):
        changed = preflight.model_copy(update={"capability_results": [capability.model_copy(update=updates)]})
        checked = _engine_result(scenarios["C2-01"], "FND-INV-CAP-001", _replace(records, changed))
        assert checked.error_code is ErrorCode.EXECUTION_UNSUPPORTED


def test_c2_01_exact_capability_tuple_passes(scenarios):
    assert _engine_result(scenarios["C2-01"], "FND-INV-CAP-001").passed


def test_review_decision_and_approved_change_bind_logical_lineage(scenarios):
    records = scenarios["C2-01"]["records"]
    assert _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001").passed
    approved = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=3)
    reviewed = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=2)
    assert reviewed.status is ChangeProposalStatus.IN_REVIEW
    assert approved.status is ChangeProposalStatus.APPROVED


def test_review_decision_for_another_logical_proposal_fails(scenarios):
    records = scenarios["C2-01"]["records"]
    reviewed = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=2)
    other = reviewed.model_copy(update={"id": "other-proposal-c2-01"})
    decision = _record(records, ObjectType.REVIEW_DECISION, "review-c2-01")
    decision = decision.model_copy(update={"change_proposal_ref": Ref(object_type=ObjectType.CHANGE_PROPOSAL, object_id=other.id, revision=other.revision)})
    checked = _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", _replace(records, decision) + (other,))
    assert checked.error_code is ErrorCode.APPROVAL_CONTENT_MISMATCH


@pytest.mark.parametrize(
    "field",
    [
        "payload",
        "native_locator_ref",
        "operation",
        "target_document_version_ref",
        "rule_pack_ref",
        "source_assessment_refs",
        "evidence_assessment_refs",
    ],
)
def test_review_to_approved_content_is_immutable(scenarios, field):
    records = scenarios["C2-01"]["records"]
    approved = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=3)
    if field == "payload":
        value = approved.payload.model_copy(update={"replacement_text": "9.99%"})
    elif field == "native_locator_ref":
        value = Ref(object_type=ObjectType.NATIVE_LOCATOR, object_id="other-locator", revision=1)
    elif field == "operation":
        value = MutationOperation.REPLACE_RUN_TEXT
    elif field == "target_document_version_ref":
        value = DocumentVersionRef(document_id="other-document", version_id="other-version", binary_hash="0" * 64)
    elif field == "rule_pack_ref":
        value = Ref(object_type=ObjectType.RULE_PACK, object_id="other-rule-pack", revision=1)
    elif field == "source_assessment_refs":
        value = []
    else:
        value = []
    changed = approved.model_copy(update={field: value})
    checked = _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", _replace(records, changed))
    assert checked.error_code is ErrorCode.APPROVAL_CONTENT_MISMATCH


def test_approved_change_must_use_immediate_successor(scenarios):
    records = scenarios["C2-01"]["records"]
    approved = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=3)
    skipped = approved.model_copy(update={"revision": 4})
    change_set = _change_set(records)
    change = change_set.authorization.approved_changes[0]
    change = change.model_copy(update={"change_proposal_ref": Ref(object_type=ObjectType.CHANGE_PROPOSAL, object_id=approved.id, revision=4)})
    change_set = _with_auth(change_set, approved_changes=[change])
    checked = _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", _replace(records, change_set) + (skipped,))
    assert checked.error_code is ErrorCode.APPROVAL_CONTENT_MISMATCH


def test_review_and_approved_states_are_required(scenarios):
    records = scenarios["C2-01"]["records"]
    reviewed = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=2)
    approved = _record(records, ObjectType.CHANGE_PROPOSAL, "ncp-proposal-c2-01", revision=3)
    for changed_reviewed, changed_approved in [
        (reviewed.model_copy(update={"status": ChangeProposalStatus.READY_FOR_REVIEW}), approved),
        (reviewed, approved.model_copy(update={"status": ChangeProposalStatus.IN_REVIEW})),
    ]:
        mutated = _replace(_replace(records, changed_reviewed), changed_approved)
        checked = _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", mutated)
        assert checked.error_code is ErrorCode.APPROVAL_CONTENT_MISMATCH


def test_nonhuman_or_nonapprove_review_cannot_authorize(scenarios):
    records = scenarios["C2-01"]["records"]
    decision = _record(records, ObjectType.REVIEW_DECISION, "review-c2-01")
    for reviewer, outcome, expected in [
        (Actor(actor_type=ActorType.AI, actor_id="ai-reviewer"), ReviewOutcome.APPROVE, ErrorCode.AI_AUTHORITY_VIOLATION),
        (decision.reviewer, ReviewOutcome.DEFER, ErrorCode.APPROVAL_REQUIRED),
    ]:
        changed = decision.model_copy(update={"reviewer": reviewer, "outcome": outcome})
        checked = _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", _replace(records, changed))
        assert checked.error_code is expected


def test_task_a_target_cannot_satisfy_task_b_release(scenarios):
    records = scenarios["C2-01"]["records"]
    task_b = _record(records, ObjectType.FOUNDATION_TASK, "task-c2-01", revision=5).model_copy(update={
        "id": "task-b",
        "status": TaskStatus.COMPLETED,
        "release_status": ReleaseStatus.ELIGIBLE,
    })
    region_a = _record(records, ObjectType.TARGET_REGION, "ncp-region-c2-01")
    region_b = region_a.model_copy(update={
        "id": "ncp-target-region-task-b",
        "task_id": "task-b",
        "verification_status": TargetVerificationStatus.BLOCKED,
    })
    checked = _engine_result(scenarios["C2-01"], "FND-INV-REL-001", records + (task_b, region_b))
    assert checked.error_code is ErrorCode.RELEASE_BLOCKED_INCOMPLETE_TARGETS


def test_task_b_cannot_use_task_a_source_or_review(scenarios):
    records = scenarios["C2-01"]["records"]
    change_set = _change_set(records).model_copy(update={"task_id": "task-b"})
    mutated = _replace(records, change_set)
    assert _engine_result(scenarios["C2-01"], "FND-INV-SRC-001", mutated).error_code is ErrorCode.SOURCE_MISSING
    assert _engine_result(scenarios["C2-01"], "FND-INV-AUTH-001", mutated).error_code is ErrorCode.APPROVAL_REQUIRED


def test_locator_from_another_task_cannot_authorize_local_change(scenarios):
    records = scenarios["C2-01"]["records"]
    locator = _record(records, ObjectType.NATIVE_LOCATOR, "ncp-locator-c2-01").model_copy(update={"task_id": "task-b"})
    checked = _engine_result(scenarios["C2-01"], "FND-INV-LOC-001", _replace(records, locator))
    assert checked.error_code is ErrorCode.LOCATOR_NOT_FOUND


def test_all_frozen_scenarios_produce_structured_invariant_results(scenarios):
    for scenario in scenarios.values():
        results = InvariantEngine().evaluate_all(_context(scenario["records"]))
        assert len(results) == 15
        assert all(item.invariant_id and item.reason for item in results)

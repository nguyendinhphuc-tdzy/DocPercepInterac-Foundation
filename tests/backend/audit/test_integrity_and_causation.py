from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from foundation.audit import (
    AuditChainValidator,
    AuditEventFactory,
    compute_integrity_hash,
    verify_integrity_hash,
)
from foundation.domain import ErrorCode, parse_audit_event
from foundation.governance.authorization import verify_authorization_digest


def test_all_frozen_authorization_digests(scenarios):
    checked = 0
    for scenario in scenarios.values():
        for record in scenario["records"]:
            if record.object_type.value == "ApprovedChangeSet":
                checked += 1
                assert verify_authorization_digest(record)
    assert checked == 8


def test_authorization_digest_detects_material_changes(scenarios):
    record = next(r for r in scenarios["C2-01"]["records"] if r.object_type.value == "ApprovedChangeSet")
    original = record.model_dump(mode="json")
    mutations = []
    for path, value in [
        (("approved_changes", 0, "operation"), "REPLACE_SDT_TEXT"),
        (("approved_changes", 0, "payload", "replacement_text"), "6.09%"),
        (("approved_changes", 0, "native_locator_ref", "object_id"), "locator-other"),
        (("rule_pack_ref", "revision"), 2),
        (("evidence_assessment_refs", 0, "revision"), 2),
    ]:
        changed = deepcopy(original["authorization"])
        cursor = changed
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        mutations.append(changed)
    assert all(compute_integrity_hash(value) != record.authorization_digest for value in mutations)


def test_all_276_frozen_event_hashes_and_chains(scenarios):
    count = 0
    for scenario in scenarios.values():
        count += len(scenario["events"])
        assert all(verify_integrity_hash(event) for event in scenario["events"])
        assert AuditChainValidator().validate(scenario["events"]).passed
    assert count == 276


def test_event_content_change_breaks_hash(scenarios):
    raw = scenarios["C2-01"]["events"][1].model_dump(mode="json")
    raw["metadata"]["summary"] += " changed"
    changed = parse_audit_event(raw)
    assert not verify_integrity_hash(changed)


def test_event_factory_hashes_and_freezes_new_event(scenarios):
    source = scenarios["C2-01"]["events"][0]
    event = AuditEventFactory.create(
        event_id="factory-event",
        event_type=source.event_type,
        occurred_at=source.occurred_at,
        actor=source.actor,
        task_id=source.task_id,
        correlation_id="factory-correlation",
        causation_event_id=None,
        document_version_refs=[],
        business_target_ids=[],
        object_refs=source.object_refs,
        input_refs=[],
        output_refs=source.output_refs,
        error_codes=[],
        metadata=source.metadata,
    )
    assert event.event_version == 1
    assert verify_integrity_hash(event)
    with pytest.raises(ValidationError):
        event.event_id = "rewritten"


def test_invalid_causation_cases_are_rejected(scenarios):
    events = list(scenarios["C2-01"]["events"][:4])
    later_null = events[1].model_copy(update={"causation_event_id": None})
    assert AuditChainValidator().validate((events[0], later_null)).error_code is ErrorCode.EVENT_CAUSATION_INVALID

    cross_task = events[1].model_copy(update={"task_id": "other-task"})
    assert not AuditChainValidator().validate((events[0], cross_task)).passed

    first = events[0].model_copy(update={"causation_event_id": events[1].event_id})
    second = events[1].model_copy(update={"causation_event_id": first.event_id})
    assert not AuditChainValidator().validate((first, second)).passed

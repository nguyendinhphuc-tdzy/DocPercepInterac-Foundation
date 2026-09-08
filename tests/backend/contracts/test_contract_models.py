from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from foundation.domain import (
    AIInteractionRecord,
    ApprovedChangeSet,
    DocumentVersion,
    NativeLocator,
    ReplayRequest,
    parse_audit_event,
    parse_record,
)


def _first_record(fixture: dict[str, object], object_type: str) -> dict[str, object]:
    return next(
        record
        for record in fixture["records"]  # type: ignore[index]
        if record["object_type"] == object_type
    )


def test_all_frozen_fixture_records_validate(contract_fixtures):
    assert len(contract_fixtures) == 8
    for path, fixture in contract_fixtures:
        assert fixture["schema_version"] == "0.1.0", path
        for record in fixture["records"]:
            parsed = parse_record(record)
            assert parsed.model_dump(mode="json", exclude_unset=True) == record, (
                path,
                record["object_type"],
                record["id"],
                record["revision"],
            )


def test_fixture_replay_requests_use_exact_internal_shape(contract_fixtures):
    replay_count = 0
    for _, fixture in contract_fixtures:
        for action in fixture["actions"]:
            if "replay_request" not in action:
                continue
            replay_count += 1
            request = ReplayRequest.model_validate(action["replay_request"])
            assert set(request.model_dump()) == {
                "execution_id",
                "approved_change_set_ref",
            }
    assert replay_count == 5


def test_all_frozen_fixture_audit_events_validate(contract_fixtures):
    event_count = 0
    for path, fixture in contract_fixtures:
        for event in fixture["audit_events"]:
            event_count += 1
            parsed = parse_audit_event(event)
            assert parsed.model_dump(mode="json", exclude_unset=True) == event, (
                path,
                event["event_id"],
                event["event_version"],
            )
    assert event_count > 0


def test_unknown_record_field_is_rejected(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "DocumentVersion"))
    record["free_form_override"] = "forbidden"
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DocumentVersion.model_validate(record)


def test_invalid_enum_is_rejected(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "DocumentVersion"))
    record["object_type"] = "UnknownRecord"
    with pytest.raises(ValidationError):
        DocumentVersion.model_validate(record)


def test_invalid_binary_hash_is_rejected(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "DocumentVersion"))
    record["binary_hash"] = "ABC"
    with pytest.raises(ValidationError):
        DocumentVersion.model_validate(record)


def test_invalid_union_discriminator_is_rejected(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "ApprovedChangeSet"))
    record["authorization"]["approved_changes"][0]["payload"]["kind"] = "FREE_FORM"
    with pytest.raises(ValidationError):
        ApprovedChangeSet.model_validate(record)


def test_invalid_reference_revision_is_rejected(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "ApprovedChangeSet"))
    record["authorization"]["review_decision_refs"][0]["revision"] = 0
    with pytest.raises(ValidationError):
        ApprovedChangeSet.model_validate(record)


def test_native_locator_address_must_match_locator_type(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "NativeLocator"))
    record["locator_type"] = "XLSX_CELL"
    with pytest.raises(ValidationError, match="locator_type"):
        NativeLocator.model_validate(record)


def test_approved_change_set_authorization_is_sealed(contract_fixtures):
    record = deepcopy(_first_record(contract_fixtures[0][1], "ApprovedChangeSet"))
    record["authorization"]["approved_changes"][0]["locator_override"] = {
        "query": "fuzzy"
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ApprovedChangeSet.model_validate(record)


def test_ai_record_has_no_execution_authority(contract_fixtures):
    ai_fixture = contract_fixtures[4][1]
    record = deepcopy(_first_record(ai_fixture, "AIInteractionRecord"))
    record["approved_change_set_ref"] = {
        "object_type": "ApprovedChangeSet",
        "object_id": "forbidden",
        "revision": 1,
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AIInteractionRecord.model_validate(record)


def test_replay_request_rejects_operation_payload_and_locator_overrides(
    contract_fixtures,
):
    fixture = contract_fixtures[0][1]
    request_data = next(
        action["replay_request"]
        for action in fixture["actions"]
        if "replay_request" in action
    )
    for field, value in {
        "operation": "REPLACE_RUN_TEXT",
        "payload": {"kind": "RUN_TEXT_REPLACEMENT", "replacement_text": "x"},
        "native_locator_ref": {
            "object_type": "NativeLocator",
            "object_id": "locator-c2-01-ncp",
            "revision": 1,
        },
    }.items():
        invalid = deepcopy(request_data)
        invalid[field] = value
        with pytest.raises(ValidationError, match="extra_forbidden"):
            ReplayRequest.model_validate(invalid)


def test_replay_request_requires_approved_change_set_reference(contract_fixtures):
    fixture = contract_fixtures[0][1]
    request_data = deepcopy(
        next(
            action["replay_request"]
            for action in fixture["actions"]
            if "replay_request" in action
        )
    )
    request_data["approved_change_set_ref"]["object_type"] = "ChangeProposal"
    with pytest.raises(ValidationError, match="ApprovedChangeSet"):
        ReplayRequest.model_validate(request_data)

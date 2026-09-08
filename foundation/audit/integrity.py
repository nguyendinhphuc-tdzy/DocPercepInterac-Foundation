"""RFC 8785 integrity functions shared by audit and qualification tooling."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

import rfc8785

from foundation.domain import AuditEvent, StrictModel


def _json_value(value: StrictModel | Mapping[str, object]) -> dict[str, object]:
    if isinstance(value, StrictModel):
        return value.model_dump(mode="json", exclude_unset=True)
    return dict(value)


def canonicalize_event_payload(value: StrictModel | Mapping[str, object]) -> bytes:
    return rfc8785.dumps(_json_value(value))


def compute_integrity_hash(value: StrictModel | Mapping[str, object]) -> str:
    return hashlib.sha256(canonicalize_event_payload(value)).hexdigest()


def audit_event_payload(event: AuditEvent) -> dict[str, object]:
    payload = event.model_dump(mode="json", exclude_unset=True)
    payload.pop("integrity_payload_hash")
    return payload


def verify_integrity_hash(event: AuditEvent) -> bool:
    actual = compute_integrity_hash(audit_event_payload(event))
    return hmac.compare_digest(actual, event.integrity_payload_hash)

"""Factory for immutable, integrity-hashed AuditEvents."""

from __future__ import annotations

from foundation.domain import (
    Actor,
    AuditEvent,
    AuditMetadata,
    BusinessTargetID,
    DocumentVersionRef,
    ErrorCode,
    EventType,
    ID,
    Ref,
    Timestamp,
)

from .integrity import compute_integrity_hash


class AuditEventFactory:
    @staticmethod
    def create(
        *,
        event_id: ID,
        event_type: EventType,
        occurred_at: Timestamp,
        actor: Actor,
        task_id: ID,
        correlation_id: ID,
        causation_event_id: ID | None,
        document_version_refs: list[DocumentVersionRef],
        business_target_ids: list[BusinessTargetID],
        object_refs: list[Ref],
        input_refs: list[Ref],
        output_refs: list[Ref],
        error_codes: list[ErrorCode],
        metadata: AuditMetadata,
    ) -> AuditEvent:
        if (event_type is EventType.TASK_CREATED) != (causation_event_id is None):
            raise ValueError("TASK_CREATED is the only event allowed null causation")
        payload = {
            "event_id": event_id,
            "event_version": 1,
            "schema_version": "0.1.0",
            "event_type": event_type.value,
            "occurred_at": occurred_at,
            "actor": actor.model_dump(mode="json"),
            "task_id": task_id,
            "correlation_id": correlation_id,
            "causation_event_id": causation_event_id,
            "document_version_refs": [item.model_dump(mode="json") for item in document_version_refs],
            "business_target_ids": list(business_target_ids),
            "object_refs": [item.model_dump(mode="json") for item in object_refs],
            "input_refs": [item.model_dump(mode="json") for item in input_refs],
            "output_refs": [item.model_dump(mode="json") for item in output_refs],
            "error_codes": [item.value for item in error_codes],
            "metadata": metadata.model_dump(mode="json"),
        }
        return AuditEvent.model_validate(
            {**payload, "integrity_payload_hash": compute_integrity_hash(payload)}
        )

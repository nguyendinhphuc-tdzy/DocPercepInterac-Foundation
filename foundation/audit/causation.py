"""Task-scoped immutable audit causation validation."""

from __future__ import annotations

from foundation.domain import AuditEvent, ErrorCode, EventType, StrictModel


class AuditChainResult(StrictModel):
    passed: bool
    error_code: ErrorCode | None
    issues: list[str]


class AuditChainValidator:
    def validate(self, events: tuple[AuditEvent, ...]) -> AuditChainResult:
        issues: list[str] = []
        by_id: dict[str, AuditEvent] = {}
        positions: dict[str, int] = {}
        for index, event in enumerate(events):
            if event.event_version != 1:
                issues.append(f"event {event.event_id} must have event_version 1")
            if event.event_id in by_id:
                issues.append(f"duplicate event_id {event.event_id}")
            by_id[event.event_id] = event
            positions[event.event_id] = index

        tasks = {event.task_id for event in events}
        for task_id in tasks:
            roots = [event for event in events if event.task_id == task_id and event.causation_event_id is None]
            task_created = [event for event in events if event.task_id == task_id and event.event_type is EventType.TASK_CREATED]
            if len(roots) != 1 or len(task_created) != 1 or roots[0].event_id != task_created[0].event_id:
                issues.append(f"task {task_id} must have exactly one TASK_CREATED root")

        for event in events:
            cause_id = event.causation_event_id
            if event.event_type is EventType.TASK_CREATED:
                if cause_id is not None:
                    issues.append(f"TASK_CREATED {event.event_id} must have null causation")
            elif cause_id is None:
                issues.append(f"event {event.event_id} must have a cause")
            if cause_id is not None:
                cause = by_id.get(cause_id)
                if cause is None:
                    issues.append(f"event {event.event_id} cause {cause_id} is missing")
                else:
                    if cause.task_id != event.task_id:
                        issues.append(f"event {event.event_id} has cross-task causation")
                    if positions[cause_id] >= positions[event.event_id]:
                        issues.append(f"event {event.event_id} cause is not earlier")
            first_failure = getattr(event.metadata, "first_material_failure_event_id", None)
            if first_failure is not None:
                failure_event = by_id.get(first_failure)
                if failure_event is None or failure_event.task_id != event.task_id:
                    issues.append(f"event {event.event_id} first material failure is unresolved")
                elif first_failure != event.event_id and positions[first_failure] >= positions[event.event_id]:
                    issues.append(f"event {event.event_id} first material failure is not earlier")

        return AuditChainResult(
            passed=not issues,
            error_code=None if not issues else ErrorCode.EVENT_CAUSATION_INVALID,
            issues=issues,
        )

validate_event_causation = AuditChainValidator().validate

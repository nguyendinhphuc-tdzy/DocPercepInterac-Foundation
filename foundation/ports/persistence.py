"""Append-only persistence interfaces for domain history and audit events."""

from typing import Protocol

from foundation.domain import AuditEvent, ID, Ref, StrictModel


class DomainRecordRepository(Protocol):
    def append(self, record: StrictModel) -> None: ...

    def get(self, reference: Ref) -> StrictModel | None: ...


class AuditRepository(Protocol):
    def append_event(self, event: AuditEvent) -> None: ...

    def events_for_task(self, task_id: ID) -> tuple[AuditEvent, ...]: ...

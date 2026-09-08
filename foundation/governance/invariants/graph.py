"""Task-aware resolution helpers for the runtime governance graph.

The frozen contract keeps reusable definitions task-neutral while records such
as assessments, targets, locators, and proposals belong to one task.  This
module keeps that distinction in one resolver so an ID reused by two tasks
cannot silently satisfy the wrong authorization.
"""

from __future__ import annotations

from collections import defaultdict

from foundation.domain import (
    DocumentVersion,
    DocumentVersionRef,
    ObjectType,
    Ref,
    StrictModel,
    TaskOwnedRecord,
)


class GovernanceGraph:
    """Resolve immutable refs with explicit task ownership and ambiguity checks."""

    def __init__(self, records: tuple[StrictModel, ...] | list[StrictModel]):
        self._records = tuple(records)
        self._by_ref: dict[tuple[ObjectType, str, int], list[StrictModel]] = defaultdict(list)
        for item in self._records:
            if hasattr(item, "object_type") and hasattr(item, "id") and hasattr(item, "revision"):
                self._by_ref[(item.object_type, item.id, item.revision)].append(item)

    def resolve(self, reference: Ref, task_id: str | None = None) -> StrictModel | None:
        candidates = self._by_ref.get(
            (reference.object_type, reference.object_id, reference.revision), []
        )
        if task_id is not None:
            candidates = [
                item
                for item in candidates
                if not isinstance(item, TaskOwnedRecord) or item.task_id == task_id
            ]
        if len(candidates) != 1:
            return None
        return candidates[0]

    def resolve_document(
        self, reference: DocumentVersionRef, task_id: str | None = None
    ) -> DocumentVersion | None:
        candidates = [
            item
            for item in self.of_type(ObjectType.DOCUMENT_VERSION)
            if isinstance(item, DocumentVersion)
            and item.document_id == reference.document_id
            and item.id == reference.version_id
            and item.binary_hash == reference.binary_hash
            and (task_id is None or item.task_id == task_id)
        ]
        if len(candidates) != 1:
            return None
        return candidates[0]

    def of_type(self, object_type: ObjectType) -> list[StrictModel]:
        return [item for item in self._records if getattr(item, "object_type", None) is object_type]

    def latest(self, object_type: ObjectType, task_id: str | None = None) -> list[StrictModel]:
        grouped: dict[tuple[str, str | None], StrictModel] = {}
        for item in self.of_type(object_type):
            item_task = item.task_id if isinstance(item, TaskOwnedRecord) else None
            if task_id is not None and item_task != task_id:
                continue
            key = (item.id, item_task)
            if key not in grouped or item.revision > grouped[key].revision:
                grouped[key] = item
        return list(grouped.values())

    def related_task_records(self, task_id: str) -> tuple[TaskOwnedRecord, ...]:
        return tuple(
            item
            for item in self._records
            if isinstance(item, TaskOwnedRecord) and item.task_id == task_id
        )

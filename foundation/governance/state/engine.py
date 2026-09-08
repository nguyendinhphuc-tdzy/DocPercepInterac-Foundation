"""Pure append-only lifecycle transition boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol

from foundation.domain import (
    Actor,
    Bool,
    ErrorCode,
    ID,
    ObjectType,
    PositiveInt,
    Ref,
    SourceAssessment,
    SourceAssessmentStatus,
    StrictModel,
    Text,
    Timestamp,
)

from .transitions import TRANSITIONS


class AuthenticatedAuthority(StrictModel):
    actor: Actor
    authenticated: Literal[True]


class TransitionContext(StrictModel):
    request_id: ID
    expected_revision: PositiveInt
    authority: AuthenticatedAuthority
    occurred_at: Timestamp


class GuardResult(StrictModel):
    passed: Bool
    evidence_refs: list[Ref]
    reason: Text


@dataclass(frozen=True)
class TransitionDecision:
    request_id: str
    previous_ref: Ref
    target_status: StrEnum
    guard_result: GuardResult
    next_record: StrictModel


class TransitionGuard(Protocol):
    def evaluate(self, record: StrictModel, target_status: StrEnum, context: TransitionContext) -> GuardResult: ...


class TransitionAuditHook(Protocol):
    def emit(self, decision: TransitionDecision) -> None: ...


class TransitionGuardRegistry:
    """Explicit policy registry for governance-sensitive transitions.

    Production callers must register the guard for each exact source/target
    edge.  The test factory is intentionally explicit and is only for bounded
    transition tests; it is not a production policy.
    """

    def __init__(self, guards: Mapping[tuple[ObjectType, StrEnum, StrEnum], TransitionGuard]):
        self._guards = dict(guards)

    @classmethod
    def for_testing(cls, guard: TransitionGuard) -> "TransitionGuardRegistry":
        return cls(
            {
                (object_type, source, target): guard
                for object_type, edges in TRANSITIONS.items()
                for source, targets in edges.items()
                for target in targets
            }
        )

    def resolve(self, object_type: ObjectType, source: StrEnum, target: StrEnum) -> TransitionGuard | None:
        return self._guards.get((object_type, source, target))


class StateTransitionError(ValueError):
    error_code = ErrorCode.INVALID_STATE_TRANSITION

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"{self.error_code.value}: {reason}")


class StateTransitionEngine:
    def __init__(self, guard_registry: TransitionGuardRegistry):
        self._guard_registry = guard_registry

    @staticmethod
    def transitions():
        return TRANSITIONS

    def transition(
        self,
        record: StrictModel,
        target_status: StrEnum,
        context: TransitionContext,
        guard: TransitionGuard,
        audit_hook: TransitionAuditHook,
        *,
        prior_decision: TransitionDecision | None = None,
    ) -> TransitionDecision:
        if not hasattr(record, "object_type") or not hasattr(record, "status") or not hasattr(record, "revision"):
            raise StateTransitionError("record has no governed lifecycle")
        object_type = record.object_type
        previous_ref = Ref(object_type=object_type, object_id=record.id, revision=record.revision)
        if prior_decision is not None and prior_decision.request_id == context.request_id:
            if prior_decision.previous_ref == previous_ref and prior_decision.target_status is target_status:
                return prior_decision
            raise StateTransitionError("idempotency key conflicts with an earlier transition")
        if context.expected_revision != record.revision:
            raise StateTransitionError("optimistic revision mismatch")
        allowed = TRANSITIONS.get(object_type, {}).get(record.status, set())
        if target_status not in allowed:
            raise StateTransitionError(f"undefined transition {record.status.value} -> {target_status.value}")
        if isinstance(record, SourceAssessment):
            if target_status is SourceAssessmentStatus.COMPLETED and record.outcome is None:
                raise StateTransitionError("COMPLETED SourceAssessment requires an outcome")
            if target_status is SourceAssessmentStatus.FAILED and record.outcome is not None:
                raise StateTransitionError("FAILED SourceAssessment requires a null outcome")
        registered_guard = self._guard_registry.resolve(object_type, record.status, target_status)
        if registered_guard is None:
            raise StateTransitionError("no registered transition guard")
        if guard is not registered_guard:
            raise StateTransitionError("caller guard is not the registered transition guard")
        guard_result = registered_guard.evaluate(record, target_status, context)
        if not guard_result.passed:
            raise StateTransitionError(guard_result.reason)
        payload = record.model_dump(mode="json", exclude_unset=True)
        payload.update(
            revision=record.revision + 1,
            status=target_status.value,
            created_at=context.occurred_at,
        )
        next_record = type(record).model_validate(payload)
        decision = TransitionDecision(
            request_id=context.request_id,
            previous_ref=previous_ref,
            target_status=target_status,
            guard_result=guard_result,
            next_record=next_record,
        )
        audit_hook.emit(decision)
        return decision

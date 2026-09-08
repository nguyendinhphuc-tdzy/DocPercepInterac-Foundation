"""Independent post-execution validation interface."""

from typing import Protocol

from foundation.domain import ExecutionResult, ValidationPlan, ValidationReport


class ValidationPort(Protocol):
    def validate(self, execution: ExecutionResult, plan: ValidationPlan) -> ValidationReport: ...

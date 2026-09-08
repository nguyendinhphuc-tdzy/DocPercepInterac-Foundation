"""Controlled replay interface; request shape cannot carry mutation overrides."""

from typing import Protocol

from foundation.domain import ExecutionResult, ReplayRequest


class ReplayPort(Protocol):
    def execute(self, request: ReplayRequest) -> ExecutionResult: ...

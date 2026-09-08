"""Semantic perception interface; no adapter implementation in B0.

The result DTO makes the application ownership boundary explicit: an adapter
returns a snapshot and its semantic objects together, and persistence remains
an application decision rather than an implicit adapter side effect.
"""

from dataclasses import dataclass
from typing import Protocol

from foundation.domain import AnalysisRun, DocumentVersion, PerceptionSnapshot, SemanticObject


@dataclass(frozen=True)
class PerceptionResult:
    """Non-contract port result; persistence is owned by the application."""

    snapshot: PerceptionSnapshot
    semantic_objects: tuple[SemanticObject, ...]


class PerceptionPort(Protocol):
    def perceive(self, document: DocumentVersion, analysis_run: AnalysisRun) -> PerceptionResult: ...

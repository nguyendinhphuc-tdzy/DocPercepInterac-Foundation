"""Semantic perception interface; no adapter implementation in B0."""

from typing import Protocol

from foundation.domain import AnalysisRun, DocumentVersion, PerceptionSnapshot


class PerceptionPort(Protocol):
    def perceive(self, document: DocumentVersion, analysis_run: AnalysisRun) -> PerceptionSnapshot: ...

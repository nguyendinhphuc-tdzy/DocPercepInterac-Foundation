"""Native preflight and semantic-to-native association interfaces."""

from typing import Protocol

from foundation.domain import (
    DocumentPreflightAssessment,
    DocumentVersion,
    NativeBinding,
    PerceptionSnapshot,
)


class NativeIdentityPort(Protocol):
    def preflight(self, document: DocumentVersion) -> DocumentPreflightAssessment: ...

    def bind(self, snapshot: PerceptionSnapshot) -> tuple[NativeBinding, ...]: ...

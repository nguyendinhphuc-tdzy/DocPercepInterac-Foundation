"""Native preflight and semantic-to-native association interfaces.

The result DTO is deliberately outside the frozen domain contract.  It keeps
preflight findings, locators, and bindings together while leaving persistence
to an explicit application boundary.
"""

from dataclasses import dataclass
from typing import Protocol

from foundation.domain import (
    DocumentPreflightAssessment,
    DocumentVersion,
    NativeBinding,
    NativeLocator,
    PerceptionSnapshot,
)


@dataclass(frozen=True)
class NativeIdentityResult:
    """Non-contract port result; adapters do not persist returned records."""

    preflight_assessment: DocumentPreflightAssessment
    native_locators: tuple[NativeLocator, ...]
    native_bindings: tuple[NativeBinding, ...]


class NativeIdentityPort(Protocol):
    def preflight(self, document: DocumentVersion) -> NativeIdentityResult: ...

    def bind(self, snapshot: PerceptionSnapshot) -> NativeIdentityResult: ...

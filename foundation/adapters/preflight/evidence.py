"""Immutable evidence bytes returned to the application, never silently stored."""

from dataclasses import dataclass
from hashlib import sha256
import rfc8785

from foundation.domain import ContentRef, DocumentPreflightAssessment


@dataclass(frozen=True)
class EvidenceArtifact:
    ref: ContentRef
    data: bytes

    @classmethod
    def create(cls, payload: dict) -> 'EvidenceArtifact':
        data = rfc8785.dumps(payload)
        digest = sha256(data).hexdigest()
        return cls(ContentRef(uri='urn:foundation:evidence:sha256:' + digest, sha256=digest, media_type='application/json'), data)


@dataclass(frozen=True)
class PreflightResult:
    """Non-contract DTO. Caller persists artifacts/assessment and emits audit events."""

    assessment: DocumentPreflightAssessment
    artifacts: tuple[EvidenceArtifact, ...]

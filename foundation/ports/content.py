"""Non-contract binary access; no URI fetching, storage writes or path fields."""

from hashlib import sha256
from typing import Protocol

from foundation.domain import DocumentVersion, ErrorCode


class ContentAccessError(RuntimeError):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        super().__init__(message)


class DocumentContentResolverPort(Protocol):
    """Application-owned lookup of pinned content; never implicit URI downloads."""

    def resolve(self, document: DocumentVersion) -> bytes: ...


def verified_bytes(document: DocumentVersion, resolver: DocumentContentResolverPort) -> bytes:
    data = resolver.resolve(document)
    if not isinstance(data, bytes):
        raise ContentAccessError(ErrorCode.INVALID_CONTRACT, 'Content resolver must return immutable bytes')
    if sha256(data).hexdigest() != document.binary_hash or document.binary_hash != document.content_ref.sha256:
        raise ContentAccessError(ErrorCode.STALE_DOCUMENT_VERSION, 'Materialized bytes differ from pinned binary hash')
    if len(data) != document.byte_length:
        raise ContentAccessError(ErrorCode.INVALID_CONTRACT, 'Registered binary length differs from materialized bytes')
    return data

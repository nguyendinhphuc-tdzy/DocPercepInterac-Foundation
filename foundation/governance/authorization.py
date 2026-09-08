"""RFC 8785 authorization digest verification for sealed change sets."""

from __future__ import annotations

import hashlib
import hmac

import rfc8785

from foundation.domain import ApprovedChangeSet, AuthorizationBinding


def canonicalize_authorization(authorization: AuthorizationBinding) -> bytes:
    return rfc8785.dumps(authorization.model_dump(mode="json", exclude_unset=True))


def compute_authorization_digest(authorization: AuthorizationBinding) -> str:
    return hashlib.sha256(canonicalize_authorization(authorization)).hexdigest()


def verify_authorization_digest(change_set: ApprovedChangeSet) -> bool:
    actual = compute_authorization_digest(change_set.authorization)
    return hmac.compare_digest(actual, change_set.authorization_digest)

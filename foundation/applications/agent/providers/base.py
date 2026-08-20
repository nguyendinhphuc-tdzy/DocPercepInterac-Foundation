"""Model provider boundary for the Foundation Agent.

The Agent owns context, intent, tools, governance and response assembly. A
provider owns *only* transport: authentication, request formatting for one
vendor API, response parsing, and mapping that vendor's failures onto the
normalized error vocabulary below.

NO FALLBACK — the strongest rule in this layer. A provider either returns the
response produced by the model the user selected, or it raises. It never
retries against another model, never substitutes another provider, and never
synthesizes a deterministic answer. Choosing a different model is exclusively a
user action.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


ProviderMessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ProviderMessage:
    """One provider-neutral chat turn.

    This is the Agent's single prompt architecture (system instruction +
    conversation turns). Providers translate it into their own wire format at
    the boundary; there is deliberately no second, provider-specific prompt
    builder anywhere in the codebase.
    """
    role: ProviderMessageRole
    content: str


@dataclass
class ProviderResponse:
    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Normalized provider errors
# ---------------------------------------------------------------------------
# Every provider maps its native failures onto exactly one of these. The Agent
# route turns `error_type` / `http_status` into the user-facing error card, so
# the vocabulary must stay stable across providers: the user should not be able
# to tell which vendor SDK failed, only which model they selected failed and
# why.


class ProviderError(Exception):
    """Base class for every normalized provider failure."""
    error_type: str = "unavailable"
    http_status: int = 503


class ProviderConfigError(ProviderError):
    """Provider is not configured or not enabled in this environment."""
    error_type = "config_missing"
    http_status = 503


class ProviderAuthError(ProviderError):
    """Credentials were rejected (HTTP 401/403)."""
    error_type = "auth_error"
    http_status = 502


class ProviderUnavailableError(ProviderError):
    """Network failure or provider-side 5xx."""
    error_type = "unavailable"
    http_status = 503


class ProviderTimeoutError(ProviderError):
    """Request exceeded the provider timeout."""
    error_type = "timeout"
    http_status = 504


class ProviderRateLimitError(ProviderError):
    """Rate limit or quota exhausted (HTTP 429)."""
    error_type = "rate_limited"
    http_status = 429


class ProviderInvalidRequestError(ProviderError):
    """Provider rejected the request as invalid (HTTP 400/404)."""
    error_type = "invalid_request"
    http_status = 502


class ProviderResponseError(ProviderError):
    """Provider returned a payload the Agent could not read."""
    error_type = "malformed_response"
    http_status = 502


class ProviderContentBlockedError(ProviderError):
    """Provider refused to answer under its own safety policy."""
    error_type = "content_blocked"
    http_status = 502


class ProviderUnsupportedError(ProviderError):
    """The selected provider cannot safely perform the requested operation.

    Raised instead of degrading governance or inventing a deterministic
    substitute (see the structured-output contract in the Agent orchestrator).
    """
    error_type = "unsupported_operation"
    http_status = 501


class ModelProvider(ABC):
    """One vendor API. Instances are created per request and hold no state."""

    provider_id: str = ""

    @abstractmethod
    def chat(self, *, messages: list[ProviderMessage], model: str) -> ProviderResponse:
        """Send one chat completion to `model` and return its response.

        Raises a ProviderError subclass on any failure. Never returns a
        response produced by a model other than `model`.
        """
        raise NotImplementedError

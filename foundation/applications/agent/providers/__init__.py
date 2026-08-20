"""Model providers for the Foundation Agent.

    Agent (one orchestrator)
      ↓
    ModelProvider
      ├── WorkbenchProvider  → Luna, Sol
      └── GeminiProvider     → Gemini 3.6 Flash, Gemini 3.5 Flash

There is exactly one Agent orchestrator and one prompt/context architecture.
Providers differ only in transport. Adding a provider must never add a second
copy of the Agent's reasoning, context building, tool semantics, or governance.
"""
from __future__ import annotations

from applications.agent.providers.base import (
    ModelProvider,
    ProviderAuthError,
    ProviderConfigError,
    ProviderContentBlockedError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderMessage,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnsupportedError,
)
from applications.agent.providers.gemini_provider import GeminiProvider
from applications.agent.providers.workbench_provider import WorkbenchProvider

_PROVIDER_CLASSES: dict[str, type[ModelProvider]] = {
    WorkbenchProvider.provider_id: WorkbenchProvider,
    GeminiProvider.provider_id: GeminiProvider,
}


def get_provider(provider_id: str) -> ModelProvider:
    """Construct the provider for this request.

    A fresh instance every call, deliberately: provider selection is per-request
    state. A request that selects Sol must not leave Workbench configuration
    behind for a following request that selects Gemini, so there is no cached
    singleton and no module-level mutable provider/model configuration anywhere.
    """
    cls = _PROVIDER_CLASSES.get(provider_id)
    if cls is None:
        raise ProviderConfigError(f"Unknown provider '{provider_id}'.")
    return cls()


__all__ = [
    "ModelProvider",
    "ProviderMessage",
    "ProviderResponse",
    "ProviderError",
    "ProviderConfigError",
    "ProviderAuthError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderInvalidRequestError",
    "ProviderResponseError",
    "ProviderContentBlockedError",
    "ProviderUnsupportedError",
    "WorkbenchProvider",
    "GeminiProvider",
    "get_provider",
]

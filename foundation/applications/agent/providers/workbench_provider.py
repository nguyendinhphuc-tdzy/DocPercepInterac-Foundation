"""WorkbenchProvider — KPMG Workbench (Azure OpenAI gateway) transport.

Wraps the pre-existing applications/workbench_client.py unchanged: same
BASE_URL, same instanceName/deployment semantics, same credentials
(WORKBENCH_SUBSCRIPTION_KEY / WORKBENCH_CHARGE_CODE), same 60s timeout. This
module adds only the mapping from Workbench's exception hierarchy onto the
normalized provider errors, so the corporate/VPN path is unchanged.

Models served: workbench_luna, workbench_sol.
"""
from __future__ import annotations

from applications.agent.providers.base import (
    ModelProvider,
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderMessage,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderConfigError,
)
from applications.workbench_client import (
    WorkbenchApiError,
    WorkbenchAuthenticationError,
    WorkbenchConfigError,
    WorkbenchNotFoundError,
    WorkbenchRateLimitError,
    WorkbenchTimeoutError,
    WorkbenchUnavailableError,
    chat_completion,
)

# Workbench's chat completion API still accepts (and uses) `temperature`; this
# is the value the Agent has always sent for document tasks. It is NOT sent to
# Gemini — see gemini_provider.py for why.
WORKBENCH_TEMPERATURE = 0.3


class WorkbenchProvider(ModelProvider):
    provider_id = "workbench"

    def chat(self, *, messages: list[ProviderMessage], model: str) -> ProviderResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        try:
            res = chat_completion(
                messages=payload,
                temperature=WORKBENCH_TEMPERATURE,
                model=model,
            )
        except WorkbenchConfigError as exc:
            raise ProviderConfigError(str(exc)) from exc
        except WorkbenchTimeoutError as exc:
            raise ProviderTimeoutError(str(exc)) from exc
        except WorkbenchAuthenticationError as exc:
            raise ProviderAuthError(str(exc)) from exc
        except WorkbenchRateLimitError as exc:
            raise ProviderRateLimitError(str(exc)) from exc
        except WorkbenchNotFoundError as exc:
            # Deployment missing. Explicitly an error, never a switch to the
            # other Workbench deployment.
            raise ProviderInvalidRequestError(str(exc)) from exc
        except WorkbenchUnavailableError as exc:
            raise ProviderUnavailableError(str(exc)) from exc
        except WorkbenchApiError as exc:
            raise ProviderResponseError(str(exc)) from exc

        return ProviderResponse(
            content=res.content,
            model=res.model,
            provider=self.provider_id,
            usage=res.usage,
        )

"""GeminiProvider — Google Gemini API transport (generateContent).

Models served: gemini_3_6_flash (gemini-3.6-flash), gemini_3_5_flash
(gemini-3.5-flash). Stable public model ids only — no `-preview` ids.

Implemented directly against the REST endpoint with `requests`, matching the
transport style of applications/workbench_client.py, so this phase adds no new
Python dependency and no second HTTP stack.

CREDENTIALS
  GEMINI_API_KEY is read from the environment, sent as the `x-goog-api-key`
  request header (never as a query parameter, so it cannot leak through a
  logged URL), and never included in any exception message or telemetry field.
  It is backend-only and is never exposed to the frontend.

SAMPLING PARAMETERS — deliberately omitted
  Current Gemini 3.x documents temperature / top_p / top_k as deprecated and
  ignored, with future model generations free to reject them outright. This
  provider therefore sends no `generationConfig` sampling block at all. This is
  a real behavioural difference from WorkbenchProvider (which still sends
  temperature, because the Azure OpenAI gateway still honours it) and is
  intentional: each provider formats requests for its own current API.

ENVIRONMENT GATING
  Gemini is intended for local/demo use with approved non-sensitive documents;
  its data-use terms differ from corporate Workbench. It is therefore disabled
  unless AI_PROVIDER_MODE explicitly enables it (see is_enabled()). When
  disabled the model still appears in the selector and still fails with an
  explicit error — it is never silently hidden and never silently re-routed.

NO FALLBACK
  Every failure raises. A failing gemini-3.6-flash request never becomes a
  gemini-3.5-flash request, a Workbench request, or a local answer.
"""
from __future__ import annotations

import os

import requests

from applications.agent.providers.base import (
    ModelProvider,
    ProviderError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderContentBlockedError,
    ProviderInvalidRequestError,
    ProviderMessage,
    ProviderRateLimitError,
    ProviderResponse,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT = 60  # seconds — matches the Workbench client

# AI_PROVIDER_MODE values that permit the Gemini provider to run. Unset defaults
# to "workbench", i.e. Gemini stays off on a corporate machine unless someone
# turns it on deliberately.
DEFAULT_PROVIDER_MODE = "workbench"
GEMINI_ENABLED_MODES = frozenset({"local", "demo", "all"})


def provider_mode() -> str:
    return (os.environ.get("AI_PROVIDER_MODE") or DEFAULT_PROVIDER_MODE).strip().lower()


def is_enabled() -> bool:
    """True when this environment is configured to allow Gemini requests."""
    return provider_mode() in GEMINI_ENABLED_MODES


def _to_gemini_payload(messages: list[ProviderMessage]) -> dict:
    """Translate the Agent's provider-neutral turns into generateContent shape.

    - `system` turns become the single `systemInstruction` (concatenated in
      order) rather than a content turn.
    - `assistant` becomes Gemini's `model` role.
    - Consecutive same-role turns are merged, because generateContent expects
      alternating user/model contents.
    """
    system_parts: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        if msg.role == "system":
            if msg.content:
                system_parts.append(msg.content)
            continue
        role = "model" if msg.role == "assistant" else "user"
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].append({"text": msg.content})
        else:
            contents.append({"role": role, "parts": [{"text": msg.content}]})

    if not contents:
        raise ProviderInvalidRequestError(
            "Request contained no user turn to send to the model."
        )
    if contents[-1]["role"] == "model":
        # A trailing prefilled model turn is rejected by the current API; the
        # Agent never builds one, so this guard exists to fail loudly rather
        # than send a malformed request if that ever changes.
        raise ProviderInvalidRequestError(
            "Request ended with a model turn, which this provider does not accept."
        )

    payload: dict = {"contents": contents}
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    return payload


def _safe_provider_message(response: requests.Response) -> str:
    """Vendor-supplied message text only — never headers, URL, or credentials."""
    try:
        body = response.json()
    except ValueError:
        return ""
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            if isinstance(msg, str):
                return msg[:300]
    return ""


def _map_http_error(response: requests.Response, model: str) -> ProviderError:
    status = response.status_code
    detail = _safe_provider_message(response)
    suffix = f" ({detail})" if detail else ""

    if status in (401, 403):
        return ProviderAuthError(f"Gemini rejected the API key.{suffix}")
    if status == 429:
        return ProviderRateLimitError(
            f"Gemini quota or rate limit exceeded for '{model}'.{suffix}"
        )
    if status == 404:
        # Model not available to this key. Explicitly an error — the other
        # Gemini model is NOT tried.
        return ProviderInvalidRequestError(
            f"Gemini model '{model}' is not available to this API key.{suffix}"
        )
    if status == 400:
        return ProviderInvalidRequestError(
            f"Gemini rejected the request as invalid.{suffix}"
        )
    if status >= 500:
        return ProviderUnavailableError(f"Gemini server error (HTTP {status}).{suffix}")
    return ProviderResponseError(f"Unexpected HTTP {status} from Gemini.{suffix}")


def _extract_text(body: dict) -> str:
    """Pull the assistant text out of a generateContent response.

    A blocked prompt or a candidate with no text is an explicit failure, not an
    empty answer — the Agent must never present silence as a model response.
    """
    if not isinstance(body, dict):
        raise ProviderResponseError("Gemini returned an unexpected response shape.")

    block_reason = (body.get("promptFeedback") or {}).get("blockReason")
    if block_reason:
        raise ProviderContentBlockedError(
            f"Gemini blocked this request (reason: {block_reason})."
        )

    candidates = body.get("candidates") or []
    if not candidates:
        raise ProviderResponseError("Gemini returned no candidates.")

    candidate = candidates[0] or {}
    parts = ((candidate.get("content") or {}).get("parts")) or []
    text = "".join(
        p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p
    )

    if not text.strip():
        finish = candidate.get("finishReason")
        if finish in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"):
            raise ProviderContentBlockedError(
                f"Gemini stopped before answering (reason: {finish})."
            )
        raise ProviderResponseError(
            f"Gemini returned no text content (finishReason: {finish or 'unknown'})."
        )

    return text


class GeminiProvider(ModelProvider):
    provider_id = "gemini"

    def chat(self, *, messages: list[ProviderMessage], model: str) -> ProviderResponse:
        if not is_enabled():
            raise ProviderConfigError(
                "Gemini models are not enabled in this environment. Set "
                "AI_PROVIDER_MODE=local to enable them for local/demo use with "
                "approved non-sensitive documents."
            )

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ProviderConfigError(
                "GEMINI_API_KEY environment variable is not set. Set it before "
                "starting the server:\n"
                "  PowerShell:  $env:GEMINI_API_KEY = '...'\n"
                "  bash:        export GEMINI_API_KEY='...'"
            )

        payload = _to_gemini_payload(messages)
        url = f"{BASE_URL}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
            )
        except requests.Timeout as exc:
            raise ProviderTimeoutError(
                f"Gemini request timed out after {REQUEST_TIMEOUT}s."
            ) from exc
        except requests.RequestException as exc:
            raise ProviderUnavailableError(
                f"Network error connecting to the Gemini API: {type(exc).__name__}"
            ) from exc

        if not response.ok:
            raise _map_http_error(response, model)

        try:
            body = response.json()
        except ValueError as exc:
            raise ProviderResponseError(
                "Gemini returned a response body that was not valid JSON."
            ) from exc

        return ProviderResponse(
            content=_extract_text(body),
            model=model,
            provider=self.provider_id,
            usage=body.get("usageMetadata", {}) or {},
        )

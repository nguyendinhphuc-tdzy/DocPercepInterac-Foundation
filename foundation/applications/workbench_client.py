"""KPMG Workbench API client — calls the Azure OpenAI chat completion
endpoint through the Workbench gateway.

Architecture note (STATUS.md, Foundation_UI_Spec_v1.0.md §36):
  - This module lives in applications/ (application layer, but shared across
    every application — not GTPS-specific), NOT in foundation/perception/ or
    foundation/output/ (core). It moved out of applications/gpts/ because
    nothing in it references GTPS/HMV/DEMO_RULES — any application (or the
    generic Agent route) can use it.
  - Credentials are read from environment variables — never hardcoded.
  - The browser never calls Workbench directly; Flask proxies via this client.

Required environment variables:
  WORKBENCH_SUBSCRIPTION_KEY  — Ocp-Apim-Subscription-Key
  WORKBENCH_CHARGE_CODE       — x-kpmg-charge-code

The model is fixed to gpt-5-4-2026-03-05-gs-ae. No silent fallback.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests


# Fixed configuration per integration-tests/Test Call Workbenh API directly 1.py
BASE_URL = "https://api.workbench.kpmg/genai/azure/openai"
MODEL = "gpt-5-6-luna-2026-07-09-gs-ae"
API_VERSION = "2024-12-01-preview"
REGION_OVERRIDE = "australiaeast"
REQUEST_TIMEOUT = 60  # seconds


class WorkbenchConfigError(Exception):
    """Raised when required environment variables are missing."""


class WorkbenchApiError(Exception):
    """Raised when the Workbench API returns a non-success status or times out."""


@dataclass
class WorkbenchResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)


def _get_credentials() -> tuple[str, str]:
    """Read subscription key and charge code from environment."""
    key = os.environ.get("WORKBENCH_SUBSCRIPTION_KEY", "")
    code = os.environ.get("WORKBENCH_CHARGE_CODE", "")
    if not key:
        raise WorkbenchConfigError(
            "WORKBENCH_SUBSCRIPTION_KEY environment variable is not set. "
            "Set it before starting the Flask server:\n"
            "  PowerShell:  $env:WORKBENCH_SUBSCRIPTION_KEY = '...'\n"
            "  bash:        export WORKBENCH_SUBSCRIPTION_KEY='...'"
        )
    if not code:
        raise WorkbenchConfigError(
            "WORKBENCH_CHARGE_CODE environment variable is not set. "
            "Set it before starting the Flask server:\n"
            "  PowerShell:  $env:WORKBENCH_CHARGE_CODE = '...'\n"
            "  bash:        export WORKBENCH_CHARGE_CODE='...'"
        )
    return key, code


def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    model: str = MODEL,
) -> WorkbenchResponse:
    """Send a chat completion request to the KPMG Workbench.

    Args:
        messages: List of {"role": ..., "content": ...} dicts.
        temperature: Sampling temperature (default 0.3 for document tasks).
        model: Specific Workbench deployment name (default Luna).

    Returns:
        WorkbenchResponse with the assistant's content and resolved model.

    Raises:
        WorkbenchConfigError: Missing credentials.
        WorkbenchApiError: Non-success HTTP response or timeout.
        requests.exceptions.*: Network-level failures.
    """
    subscription_key, charge_code = _get_credentials()

    url = f"{BASE_URL}/deployments/{model}/chat/completions"
    params = {"api-version": API_VERSION}

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "x-kpmg-charge-code": charge_code,
        "x-kpmg-region-override": REGION_OVERRIDE,
        "Content-Type": "application/json",
    }

    json_body = {
        "messages": messages,
        "temperature": temperature,
    }

    try:
        response = requests.post(
            url, headers=headers, params=params, json=json_body, timeout=REQUEST_TIMEOUT
        )
    except requests.Timeout as exc:
        raise WorkbenchApiError(f"Workbench request timed out after {REQUEST_TIMEOUT}s.") from exc
    except requests.RequestException as exc:
        raise WorkbenchApiError(f"Network error connecting to Workbench: {exc}") from exc

    if not response.ok:
        # Build a helpful error message without leaking credentials
        try:
            error_body = response.json()
        except Exception:
            error_body = {"raw": response.text[:500]}

        if response.status_code == 401:
            detail = "Subscription key was rejected (verify WORKBENCH_SUBSCRIPTION_KEY)."
        elif response.status_code == 403:
            detail = "Request denied (verify WORKBENCH_CHARGE_CODE and subscription access)."
        elif response.status_code == 404:
            detail = f"Deployment '{model}' not found — do NOT silently fall back to another model."
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            detail = f"Rate limited. Retry-After: {retry_after}s."
        elif response.status_code >= 500:
            detail = "Workbench server error (likely transient)."
        else:
            detail = f"Unexpected HTTP {response.status_code}."

        raise WorkbenchApiError(
            f"Workbench API error: {detail} "
            f"Response: {error_body}"
        )

    body = response.json()

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorkbenchApiError(
            f"Unexpected response shape from Workbench: {exc}"
        ) from exc

    return WorkbenchResponse(
        content=content,
        model=model,
        usage=body.get("usage", {}),
    )

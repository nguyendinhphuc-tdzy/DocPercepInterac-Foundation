"""Standalone smoke test: call the KPMG Workbench Azure OpenAI API directly.

This is an INTEGRATION SMOKE TEST ONLY. It is not part of the Document
Perception & Interaction Foundation core (foundation/perception,
foundation/output, foundation/eval) and introduces no Workbench-specific
logic there. It exists purely to answer, from the command line:

    1. Can Python reach the KPMG Workbench endpoint?
    2. Is the subscription key accepted?
    3. Are the configured KPMG charge code and region override accepted?
    4. Is the selected Azure OpenAI deployment callable?
    5. Does a basic chat completion come back successfully?

Run it with:

    python "Test Call Workbenh API directly 1.py"

Required environment variables (never hardcode these — read from the
environment only):

    WORKBENCH_SUBSCRIPTION_KEY   Ocp-Apim-Subscription-Key for Workbench
    WORKBENCH_CHARGE_CODE        x-kpmg-charge-code for Workbench

The script fails fast with a clear message if either is unset. No
env var value is ever printed. TLS verification is never disabled.

Authentication note: the simplest working mechanism for this endpoint is
the three headers below (subscription key + charge code + region
override) — no NTLM. Do not add `requests_ntlm`/`HttpNtlmAuth` unless a
real request against this endpoint fails specifically because NTLM
authentication is required (e.g. a 401 with an NTLM/Negotiate challenge in
`WWW-Authenticate`); if that happens, diagnose and add it separately
rather than adding it speculatively here.
"""
from __future__ import annotations

import json
import os
import sys

import requests

# --- Fixed Workbench configuration (per KPMG Workbench API contract) --------

BASE_URL = "https://api.workbench.kpmg/genai/azure/openai"
MODEL = "gpt-5-4-2026-03-05-gs-ae"
API_VERSION = "2024-12-01-preview"
REGION_OVERRIDE = "australiaeast"

# Headers whose values must never be echoed to stdout, even if the server
# happens to reflect one back.
_SENSITIVE_HEADER_MARKERS = ("key", "token", "authorization", "cookie", "secret")


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"ERROR: required environment variable '{name}' is not set.", file=sys.stderr)
        print(
            "Set it before running this script, e.g.:\n"
            f"  Windows PowerShell : $env:{name} = '...'\n"
            f"  bash               : export {name}='...'",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def _print_safe_response_headers(headers: "requests.structures.CaseInsensitiveDict") -> None:
    print("Response headers (credential-bearing values excluded):")
    for key, value in headers.items():
        if any(marker in key.lower() for marker in _SENSITIVE_HEADER_MARKERS):
            print(f"  {key}: <redacted>")
        else:
            print(f"  {key}: {value}")


def main() -> None:
    subscription_key = _get_required_env("WORKBENCH_SUBSCRIPTION_KEY")
    charge_code = _get_required_env("WORKBENCH_CHARGE_CODE")

    url = f"{BASE_URL}/deployments/{MODEL}/chat/completions"
    params = {"api-version": API_VERSION}

    headers = {
        "Ocp-Apim-Subscription-Key": subscription_key,
        "x-kpmg-charge-code": charge_code,
        "x-kpmg-region-override": REGION_OVERRIDE,
        "Content-Type": "application/json",
    }

    json_body = {
        "messages": [
            {"role": "system", "content": "You are Innovation Business Analysis."},
            {"role": "user", "content": "BA là gì?"},
        ]
    }

    print("=== Workbench API Test ===")
    print(f"Model: {MODEL}")
    print(f"API Version: {API_VERSION}")
    print(f"Region override: {REGION_OVERRIDE}")
    print(f"URL: {url}")
    print()

    try:
        response = requests.post(url, headers=headers, params=params, json=json_body, timeout=300)
    except requests.exceptions.ConnectTimeout:
        print("ERROR: connection to Workbench timed out while connecting.", file=sys.stderr)
        print("Likely cause: network/VPN/proxy cannot reach api.workbench.kpmg.", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.ReadTimeout:
        print("ERROR: Workbench did not respond within the 300s timeout.", file=sys.stderr)
        print("Likely cause: model is slow/overloaded, or the request is stuck server-side.", file=sys.stderr)
        sys.exit(2)
    except requests.exceptions.ConnectionError as exc:
        print(f"ERROR: could not connect to Workbench: {exc}", file=sys.stderr)
        print(
            "Likely cause: DNS/network/VPN issue, or the endpoint is unreachable "
            "from this machine.",
            file=sys.stderr,
        )
        sys.exit(2)
    except requests.exceptions.RequestException as exc:
        # Catch-all for other requests-level failures (e.g. malformed URL) —
        # reported, not swallowed.
        print(f"ERROR: request to Workbench failed: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"Status: {response.status_code}")
    print()
    _print_safe_response_headers(response.headers)
    print()

    # Try to parse JSON regardless of status code — Workbench error bodies
    # are typically JSON too, and we want to show them either way.
    body_json = None
    try:
        body_json = response.json()
    except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
        print("=== Response body (not valid JSON) ===")
        print(response.text)
        print()

    if not response.ok:
        print("=== Workbench call FAILED ===")
        if response.status_code == 401:
            print(
                "HTTP 401 Unauthorized — the subscription key was rejected (or missing). "
                "Verify WORKBENCH_SUBSCRIPTION_KEY is correct and active. If the response "
                "headers above show an NTLM/Negotiate challenge in WWW-Authenticate, this "
                "endpoint may require NTLM auth — that would need to be diagnosed and added "
                "separately, not assumed."
            )
        elif response.status_code == 403:
            print(
                "HTTP 403 Forbidden — the subscription key was accepted but the request was "
                "denied. Likely cause: WORKBENCH_CHARGE_CODE is invalid/not authorized for "
                "this subscription, the region override 'australiaeast' is not permitted, or "
                "this subscription lacks access to this deployment."
            )
        elif response.status_code == 404:
            print(
                f"HTTP 404 Not Found — deployment '{MODEL}' was not found at this endpoint. "
                "Per requirements, do NOT silently fall back to another model — report this "
                "and stop. Verify the exact deployment name with the Workbench team."
            )
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            print(
                "HTTP 429 Too Many Requests — rate limited by Workbench."
                + (f" Retry-After: {retry_after}s" if retry_after else "")
            )
        elif response.status_code >= 500:
            print(
                f"HTTP {response.status_code} — Workbench server-side error. "
                "This is likely transient; retry later or escalate to the Workbench team "
                "if it persists."
            )
        else:
            print(f"HTTP {response.status_code} — unexpected non-success status.")

        if body_json is not None:
            print()
            print("=== Response body (JSON) ===")
            print(json.dumps(body_json, indent=2, ensure_ascii=False))
        sys.exit(1)

    # --- Success path ---------------------------------------------------
    if body_json is None:
        print("=== Workbench call succeeded, but response body was not valid JSON ===")
        sys.exit(1)

    try:
        assistant_message = body_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("=== Unexpected response shape (not a standard chat completion) ===")
        print(json.dumps(body_json, indent=2, ensure_ascii=False))
        sys.exit(1)

    print("=== Assistant Response ===")
    print(assistant_message)


if __name__ == "__main__":
    main()

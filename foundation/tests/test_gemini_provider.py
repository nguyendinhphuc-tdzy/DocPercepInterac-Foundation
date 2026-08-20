"""GeminiProvider unit tests — request shaping, response parsing, error mapping.

Every test mocks `requests.post`, so nothing here touches the network or needs
a real API key. The live smoke test lives in test_gemini_live.py and is skipped
unless GEMINI_API_KEY is genuinely present.

Two properties matter most and are asserted repeatedly:
  1. No credential ever appears in an exception message or a request URL.
  2. Every failure raises. The provider never returns a substitute answer and
     never retries against the other Gemini model.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from applications.agent.providers import (  # noqa: E402
    ProviderAuthError,
    ProviderConfigError,
    ProviderContentBlockedError,
    ProviderInvalidRequestError,
    ProviderMessage,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from applications.agent.providers.gemini_provider import (  # noqa: E402
    GeminiProvider,
    _to_gemini_payload,
)
from tests.gemini_mocks import (  # noqa: E402
    gemini_blocked_response,
    gemini_error_response,
    gemini_malformed_response,
    gemini_non_json_response,
    gemini_ok_response,
)

TEST_KEY = "test-key-not-a-real-credential"

MESSAGES = [
    ProviderMessage(role="system", content="You are the Foundation Agent."),
    ProviderMessage(role="user", content="Summarize the selected element."),
]


# ============================================================================
# REQUEST SHAPING
# ============================================================================

def test_payload_maps_system_turn_to_system_instruction():
    payload = _to_gemini_payload(MESSAGES)
    assert payload["systemInstruction"] == {
        "parts": [{"text": "You are the Foundation Agent."}]
    }
    assert payload["contents"] == [
        {"role": "user", "parts": [{"text": "Summarize the selected element."}]}
    ]


def test_payload_maps_assistant_turn_to_model_role():
    payload = _to_gemini_payload([
        ProviderMessage(role="user", content="first"),
        ProviderMessage(role="assistant", content="reply"),
        ProviderMessage(role="user", content="second"),
    ])
    assert [c["role"] for c in payload["contents"]] == ["user", "model", "user"]


def test_payload_merges_consecutive_same_role_turns():
    payload = _to_gemini_payload([
        ProviderMessage(role="user", content="a"),
        ProviderMessage(role="user", content="b"),
    ])
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["parts"] == [{"text": "a"}, {"text": "b"}]


def test_payload_rejects_trailing_prefilled_model_turn():
    """A prefilled model turn as the last content is rejected by the current API."""
    with pytest.raises(ProviderInvalidRequestError):
        _to_gemini_payload([
            ProviderMessage(role="user", content="hi"),
            ProviderMessage(role="assistant", content="prefilled"),
        ])


def test_payload_omits_deprecated_sampling_parameters():
    """temperature / top_p / top_k are deprecated-and-ignored on Gemini 3.x and
    may be rejected outright by later generations, so none are ever sent."""
    payload = _to_gemini_payload(MESSAGES)
    assert "generationConfig" not in payload
    serialized = str(payload)
    for deprecated in ("temperature", "topP", "top_p", "topK", "top_k"):
        assert deprecated not in serialized


def test_api_key_is_sent_as_header_never_in_url(monkeypatch, gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_ok_response()
        GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")

    url = mock_post.call_args.args[0]
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["x-goog-api-key"] == TEST_KEY
    assert TEST_KEY not in url
    assert "key=" not in url
    assert url.endswith("/models/gemini-3.6-flash:generateContent")


def test_each_gemini_model_is_called_by_its_own_name(gemini_enabled):
    """3.6 calls 3.6 and 3.5 calls 3.5 — the models never stand in for each other."""
    for model in ("gemini-3.6-flash", "gemini-3.5-flash"):
        with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
            mock_post.return_value = gemini_ok_response()
            GeminiProvider().chat(messages=MESSAGES, model=model)
            assert mock_post.call_count == 1
            assert mock_post.call_args.args[0].endswith(f"/models/{model}:generateContent")


# ============================================================================
# SUCCESS
# ============================================================================

def test_success_returns_model_text_and_identity(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_ok_response("Gemini says hello.")
        res = GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")

    assert res.content == "Gemini says hello."
    assert res.model == "gemini-3.6-flash"
    assert res.provider == "gemini"
    assert res.usage["promptTokenCount"] == 12


def test_success_concatenates_multiple_text_parts(gemini_enabled):
    payload = {
        "candidates": [
            {
                "content": {"parts": [{"text": "part one "}, {"text": "part two"}]},
                "finishReason": "STOP",
            }
        ]
    }
    from tests.gemini_mocks import FakeResponse

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = FakeResponse(200, payload)
        res = GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")

    assert res.content == "part one part two"


# ============================================================================
# CONFIGURATION GATING
# ============================================================================

def test_disabled_environment_raises_config_error(monkeypatch):
    """Unset AI_PROVIDER_MODE means Gemini is off — explicit error, no request."""
    monkeypatch.delenv("AI_PROVIDER_MODE", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", TEST_KEY)

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        with pytest.raises(ProviderConfigError) as exc:
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")
        mock_post.assert_not_called()
    assert "AI_PROVIDER_MODE" in str(exc.value)


def test_corporate_provider_mode_raises_config_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_MODE", "workbench")
    monkeypatch.setenv("GEMINI_API_KEY", TEST_KEY)

    with pytest.raises(ProviderConfigError):
        GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_missing_api_key_raises_config_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_MODE", "local")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        with pytest.raises(ProviderConfigError) as exc:
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")
        mock_post.assert_not_called()
    assert "GEMINI_API_KEY" in str(exc.value)


# ============================================================================
# ERROR MAPPING
# ============================================================================

def test_timeout_maps_to_provider_timeout(gemini_enabled):
    import requests

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.side_effect = requests.Timeout("read timed out")
        with pytest.raises(ProviderTimeoutError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_network_error_maps_to_unavailable(gemini_enabled):
    import requests

    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.side_effect = requests.ConnectionError("connection refused")
        with pytest.raises(ProviderUnavailableError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failure_maps_to_auth_error(gemini_enabled, status):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(status, "API key not valid.")
        with pytest.raises(ProviderAuthError) as exc:
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")
    assert TEST_KEY not in str(exc.value)


def test_quota_exhausted_maps_to_rate_limited(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(
            429, "Quota exceeded for quota metric 'Generate Content API requests'."
        )
        with pytest.raises(ProviderRateLimitError) as exc:
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")
    assert exc.value.error_type == "rate_limited"
    assert exc.value.http_status == 429


def test_invalid_request_maps_to_invalid_request(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(
            400, "Invalid JSON payload received."
        )
        with pytest.raises(ProviderInvalidRequestError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_unknown_model_404_raises_and_does_not_try_the_other_gemini(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(404, "models/x is not found.")
        with pytest.raises(ProviderInvalidRequestError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")
        # Exactly one HTTP call: no second attempt against gemini-3.5-flash.
        assert mock_post.call_count == 1


def test_server_error_maps_to_unavailable(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_error_response(503, "The model is overloaded.")
        with pytest.raises(ProviderUnavailableError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_malformed_response_raises_rather_than_returning_empty(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_malformed_response()
        with pytest.raises(ProviderResponseError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_non_json_body_raises_response_error(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_non_json_response()
        with pytest.raises(ProviderResponseError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_blocked_prompt_raises_content_blocked(gemini_enabled):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = gemini_blocked_response("SAFETY")
        with pytest.raises(ProviderContentBlockedError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


def test_safety_finish_reason_with_no_text_raises_content_blocked(gemini_enabled):
    from tests.gemini_mocks import FakeResponse

    payload = {"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]}
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = FakeResponse(200, payload)
        with pytest.raises(ProviderContentBlockedError):
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")


# ============================================================================
# CREDENTIAL HYGIENE
# ============================================================================

@pytest.mark.parametrize(
    "response_factory",
    [
        lambda: gemini_error_response(401, "API key not valid. Please pass a valid API key."),
        lambda: gemini_error_response(429, "Quota exceeded."),
        lambda: gemini_error_response(400, "Invalid argument."),
        lambda: gemini_error_response(500, "Internal error."),
        lambda: gemini_malformed_response(),
        lambda: gemini_non_json_response(),
        lambda: gemini_blocked_response(),
    ],
)
def test_no_credentials_or_endpoints_leak_into_errors(gemini_enabled, response_factory):
    with patch("applications.agent.providers.gemini_provider.requests.post") as mock_post:
        mock_post.return_value = response_factory()
        with pytest.raises(Exception) as exc:
            GeminiProvider().chat(messages=MESSAGES, model="gemini-3.6-flash")

    text = str(exc.value)
    assert TEST_KEY not in text
    assert "x-goog-api-key" not in text
    assert "generativelanguage.googleapis.com" not in text

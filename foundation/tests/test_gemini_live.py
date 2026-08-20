"""LIVE Gemini smoke test — real network, real credentials, no mocks.

SKIPPED unless GEMINI_API_KEY is actually present in the environment. This
file exists so that "Gemini live verified" can only ever be claimed by a run
that genuinely reached the Gemini API; a skipped run is not a pass, and the
evaluation report must record it as unverified.

Run it deliberately:

    $env:GEMINI_API_KEY = '...'
    $env:AI_PROVIDER_MODE = 'local'
    .venv/Scripts/python.exe -m pytest tests/test_gemini_live.py -v

PRIVACY: this test sends a fixed, non-sensitive prompt. Never point a live
provider test at client document content.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from applications.agent.providers import ProviderMessage  # noqa: E402
from applications.agent.providers.gemini_provider import GeminiProvider  # noqa: E402

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY not set — live Gemini verification not performed",
)

PROMPT = [
    ProviderMessage(
        role="system",
        content="You are a test harness. Answer with a single short sentence.",
    ),
    ProviderMessage(role="user", content="Reply with the word READY and nothing else."),
]


@pytest.fixture(autouse=True)
def _enable_gemini(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_MODE", "local")


@pytest.mark.parametrize("model", ["gemini-3.6-flash", "gemini-3.5-flash"])
def test_live_gemini_returns_a_real_response(model):
    res = GeminiProvider().chat(messages=PROMPT, model=model)

    assert res.provider == "gemini"
    # The response is attributed to exactly the model that was requested.
    assert res.model == model
    assert res.content.strip(), "live provider returned empty content"
    # A real call reports token usage; a stub would not.
    assert res.usage, "live provider returned no usageMetadata"

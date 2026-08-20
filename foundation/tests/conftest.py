"""Shared pytest fixtures for the Foundation test suite."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def gemini_enabled(monkeypatch):
    """Put the process in the environment state that permits Gemini requests.

    Gemini is off unless AI_PROVIDER_MODE says otherwise, so any test that
    exercises the Gemini path must opt in explicitly — exactly as an operator
    would have to. The key here is a dummy: every test that uses this fixture
    also mocks the HTTP layer.
    """
    monkeypatch.setenv("AI_PROVIDER_MODE", "local")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    yield

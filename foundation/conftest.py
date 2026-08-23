"""
Deterministic test environment for the Foundation suite.
========================================================
Location: foundation/conftest.py

`pytest foundation -q` must produce the same result on every machine, whatever a
developer happens to have in their `.env`. Before this file existed, a developer
with `STORAGE_BACKEND=supabase` (the setting production needs) saw dozens of
failures and errors that said nothing about the code, and a developer with a
real `GEMINI_API_KEY` silently ran live-network tests as part of a normal run.

pytest imports the root conftest before any test module — and therefore before
`config.py` is first imported — so pinning the environment here is what makes the
suite deterministic. `load_dotenv()` in config.py does not override variables
that are already set, so these values win over `.env` without touching the file.

Test defaults
    ENVIRONMENT=testing, STORAGE_BACKEND=local, DATABASE_BACKEND=local

Live-service credentials are blanked rather than deleted: an unset variable would
simply be re-populated from `.env` when config.py loads it, while a variable that
is present-but-empty is left alone by dotenv and reads as "not configured".

Opt in to tests that need real services with:

    FOUNDATION_LIVE_TESTS=1 pytest foundation -q

which keeps the developer's real credentials in place, so the live Supabase and
live Gemini tests can run deliberately instead of by accident.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

FOUNDATION_ROOT = Path(__file__).resolve().parent
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

# Settings the suite is written against. These are applied unconditionally.
TEST_ENVIRONMENT = {
    "ENVIRONMENT": "testing",
    "STORAGE_BACKEND": "local",
    "DATABASE_BACKEND": "local",
    "ALLOWED_ORIGINS": "http://localhost:5173",
}

# Credentials that would otherwise point a normal test run at a live service.
LIVE_CREDENTIAL_KEYS = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL",
    "GEMINI_API_KEY",
    "WORKBENCH_SUBSCRIPTION_KEY",
    "WORKBENCH_CHARGE_CODE",
    "AI_PROVIDER_MODE",
)

LIVE_TESTS_ENABLED = os.environ.get("FOUNDATION_LIVE_TESTS", "").strip().lower() in (
    "1", "true", "yes")

# What the developer actually had, kept so an opt-in live test can ask for it
# explicitly rather than depending on ambient state.
DEVELOPER_ENVIRONMENT = {key: os.environ.get(key) for key in LIVE_CREDENTIAL_KEYS}


def _pin_test_environment() -> None:
    for key, value in TEST_ENVIRONMENT.items():
        os.environ[key] = value
    if LIVE_TESTS_ENABLED:
        return
    for key in LIVE_CREDENTIAL_KEYS:
        # Empty, not absent: dotenv skips keys that are already present, so this
        # is what actually prevents `.env` from re-supplying them at import time.
        os.environ[key] = ""


_pin_test_environment()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live_supabase: needs a real Supabase project (FOUNDATION_LIVE_TESTS=1)")
    config.addinivalue_line(
        "markers", "live_gemini: needs a real Gemini API key (FOUNDATION_LIVE_TESTS=1)")


def pytest_collection_modifyitems(config: pytest.Config, items) -> None:
    """Live-service tests are opt-in; a skipped live test is not a pass."""
    if LIVE_TESTS_ENABLED:
        return
    skip = pytest.mark.skip(
        reason="live-service test — run with FOUNDATION_LIVE_TESTS=1 and real credentials")
    for item in items:
        if "live_supabase" in item.keywords or "live_gemini" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def test_environment() -> dict:
    """The pinned settings, for a test that wants to assert on them."""
    return dict(TEST_ENVIRONMENT)


@pytest.fixture
def live_supabase_credentials():
    """Real Supabase credentials, or skip. Only for tests marked `live_supabase`."""
    url = DEVELOPER_ENVIRONMENT.get("SUPABASE_URL")
    key = DEVELOPER_ENVIRONMENT.get("SUPABASE_SERVICE_ROLE_KEY")
    if not LIVE_TESTS_ENABLED or not url or not key:
        pytest.skip("live Supabase credentials not available")
    return {"SUPABASE_URL": url, "SUPABASE_SERVICE_ROLE_KEY": key}


@pytest.fixture(autouse=True)
def _isolated_repository_singleton():
    """Every test starts from a clean repository/storage singleton.

    The bundle caches the backend it built from config; a test that changes the
    backend would otherwise inherit the previous test's adapter.
    """
    yield
    try:
        from adapters.repository import reset_repositories

        reset_repositories()
    except Exception:
        pass

"""Mocked Gemini API responses shared by the Agent provider test suites.

These build the shapes `requests.post` returns, so tests exercise the real
GeminiProvider parsing/error-mapping code without a network call or an API key.
No real credentials are ever involved here — the live smoke test is separate
and is skipped unless GEMINI_API_KEY is actually present.
"""
from __future__ import annotations

import json
from typing import Any, Optional


class FakeResponse:
    """Minimal stand-in for requests.Response as GeminiProvider uses it."""

    def __init__(self, status_code: int, payload: Any = None, text: Optional[str] = None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 400
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload or {})

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("No JSON object could be decoded")
        return self._payload


def gemini_ok_response(text: str = "Mocked Gemini answer.") -> FakeResponse:
    return FakeResponse(
        200,
        {
            "candidates": [
                {
                    "content": {"role": "model", "parts": [{"text": text}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 6},
        },
    )


def gemini_error_response(status_code: int, message: str, status: str = "") -> FakeResponse:
    """A Gemini REST error envelope, as the API actually returns it."""
    return FakeResponse(
        status_code,
        {"error": {"code": status_code, "message": message, "status": status}},
    )


def gemini_blocked_response(reason: str = "SAFETY") -> FakeResponse:
    return FakeResponse(200, {"promptFeedback": {"blockReason": reason}})


def gemini_malformed_response() -> FakeResponse:
    """200 OK with a body that carries no candidates at all."""
    return FakeResponse(200, {"unexpected": "shape"})


def gemini_non_json_response() -> FakeResponse:
    """200 OK whose body is not JSON (e.g. an intercepting proxy's HTML page)."""
    return FakeResponse(200, None, text="<html>not json</html>")

"""Flask app factory — Access layer (STATUS.md: Flask, not FastAPI).

Run with: cd foundation && .venv/Scripts/python.exe -m api.app
"""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.routes.process import process_bp  # noqa: E402
from api.routes.agent import agent_bp  # noqa: E402


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(process_bp)
    app.register_blueprint(agent_bp)

    @app.after_request
    def add_cors_headers(response):
        # Local/air-gapped tool (STATUS.md) — no auth boundary between the
        # Vite dev server and this API, so a permissive dev CORS policy is
        # fine. Vite's port floats (5173, 5174, ...) so a fixed origin
        # allowlist would be brittle here; reflect whatever Origin sent.
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.route("/api/<path:_unused>", methods=["OPTIONS"])
    def cors_preflight(_unused):
        return "", 204

    return app


if __name__ == "__main__":
    create_app().run(port=5000, debug=True)

"""
Flask app factory — Access layer (Phase DEPLOY-1).
=================================================
Location: foundation/api/app.py

Production-hardened Flask application factory:
- Validates environment configuration on startup (fail-closed in production).
- Strict CORS origin enforcement (allowlist in production; permissive in dev).
- Health check endpoints: /health, /health/database, /health/storage (zero secret leakage).
- Standardized request dispatch to blueprints.
"""
from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import get_config  # noqa: E402
from adapters.storage import get_storage  # noqa: E402
from adapters.repository import get_repositories  # noqa: E402
from api.routes.documents import documents_bp  # noqa: E402
from api.routes.gpts import gpts_bp  # noqa: E402
from api.routes.agent import agent_bp  # noqa: E402
from api.routes.pilot import pilot_bp  # noqa: E402


def create_app() -> Flask:
    config = get_config()
    # Validate production invariants on app boot
    config.validate()

    app = Flask(__name__)
    app.register_blueprint(documents_bp)
    app.register_blueprint(gpts_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(pilot_bp)

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        allowed = config.allowed_origins

        if config.is_production:
            if origin and origin in allowed:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
        else:
            # In development, reflect origin or allow local dev origins
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        return response

    @app.route("/api/<path:_unused>", methods=["OPTIONS"])
    def cors_preflight(_unused):
        return "", 204

    @app.route("/api/health", methods=["GET"])
    @app.route("/health", methods=["GET"])
    def health_check():
        """General application health check (zero secret leakage)."""
        return jsonify(config.get_safe_health_dict()), 200

    @app.route("/api/health/database", methods=["GET"])
    @app.route("/health/database", methods=["GET"])
    def database_health():
        """Database connectivity health check."""
        repos = get_repositories(config)
        ok, msg = repos.check_health()
        status_code = 200 if ok else 503
        return jsonify({
            "status": "ok" if ok else "error",
            "backend": config.database_backend,
            "message": msg,
        }), status_code

    @app.route("/api/health/storage", methods=["GET"])
    @app.route("/health/storage", methods=["GET"])
    def storage_health():
        """Storage connectivity health check."""
        storage = get_storage(config)
        ok, msg = storage.check_health()
        status_code = 200 if ok else 503
        return jsonify({
            "status": "ok" if ok else "error",
            "backend": config.storage_backend,
            "message": msg,
        }), status_code

    return app


if __name__ == "__main__":
    cfg = get_config()
    create_app().run(host="0.0.0.0", port=cfg.port, debug=(not cfg.is_production))

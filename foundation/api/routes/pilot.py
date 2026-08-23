"""
Pilot instrumentation routes (Phase DEPLOY-1).
==============================================
Location: foundation/api/routes/pilot.py

Access-layer surface for the Agent pilot phase:
- POST /api/pilot/event    — ingest a UI-origin pilot event.
- GET  /api/pilot/scenarios — list the controlled pilot scenario definitions.

Maintains fail-open telemetry guarantee across both file logs and repository sink.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.pilot.event_log import PilotEventLogger  # noqa: E402
from adapters.repository import PilotEventRecord, get_repositories  # noqa: E402

pilot_bp = Blueprint("pilot", __name__)

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "docs" / "evaluation" / "agent-pilot" / "scenarios"


def _get_user_id() -> str:
    return request.headers.get("X-User-Id", "anonymous")


@pilot_bp.post("/api/pilot/event")
def ingest_event():
    body = request.get_json(silent=True) or {}
    event_type = body.get("event_type")
    if not event_type or not isinstance(event_type, str):
        return jsonify({"error": "event_type is required."}), 400

    fields = {k: v for k, v in body.items() if k != "event_type"}
    fields["origin"] = "frontend"
    user_id = _get_user_id()

    # Emit to file sink (existing)
    record = PilotEventLogger.emit(event_type, **fields)

    # Also emit to repository sink (fail-open)
    try:
        repos = get_repositories()
        repos.pilot.emit(
            PilotEventRecord(
                event_type=event_type,
                session_id=fields.get("session_id"),
                user_id=user_id,
                model_id=fields.get("model_id"),
                provider=fields.get("provider"),
                status=fields.get("status"),
                payload=fields,
            )
        )
    except Exception:
        pass

    return jsonify({"status": "recorded" if record is not None else "dropped"})


@pilot_bp.get("/api/pilot/scenarios")
def list_scenarios():
    scenarios = []
    if SCENARIOS_DIR.is_dir():
        for path in sorted(SCENARIOS_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                scenarios.append({
                    "scenario_id": data.get("scenario_id"),
                    "category": data.get("category"),
                    "task": data.get("task"),
                })
            except (OSError, json.JSONDecodeError):
                continue
    return jsonify({"scenarios": scenarios})

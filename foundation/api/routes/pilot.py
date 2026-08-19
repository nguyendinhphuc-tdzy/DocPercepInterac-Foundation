"""Pilot instrumentation routes.

Access-layer surface for the Agent pilot phase (docs/evaluation/agent-pilot/):
- POST /api/pilot/event    — ingest a UI-origin pilot event (citation click,
  reveal, task lifecycle, feedback). Server-origin events (intent resolved,
  proposal lifecycle, writes) are emitted directly from applications/agent/
  and do not go through this route.
- GET  /api/pilot/scenarios — list the controlled pilot scenario definitions
  (metadata only, no document content) for an optional scenario launcher UI.

This route intentionally does not import from perception/, output/, or
applications/gpts/ — it is pilot-evaluation plumbing, not a document
capability, and must stay generic per the same layer boundary the agent
route follows.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.pilot.event_log import PilotEventLogger  # noqa: E402

pilot_bp = Blueprint("pilot", __name__)

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "docs" / "evaluation" / "agent-pilot" / "scenarios"


@pilot_bp.post("/api/pilot/event")
def ingest_event():
    body = request.get_json(silent=True) or {}
    event_type = body.get("event_type")
    if not event_type or not isinstance(event_type, str):
        return jsonify({"error": "event_type is required."}), 400

    fields = {k: v for k, v in body.items() if k != "event_type"}
    fields["origin"] = "frontend"
    record = PilotEventLogger.emit(event_type, **fields)

    # Fail-open at the API boundary too: instrumentation must never surface
    # a hard error that could distract from (or be confused with) a real
    # Agent failure during a pilot session.
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

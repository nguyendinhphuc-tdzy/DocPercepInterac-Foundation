from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from foundation.domain import ReplayRequest, parse_audit_event, parse_record


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATHS = tuple(sorted((ROOT / "docs/contracts/examples").glob("[0-9][0-9]-*.yaml")))


@pytest.fixture(scope="session")
def scenarios():
    result = {}
    for path in FIXTURE_PATHS:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        result[raw["scenario_id"]] = {
            "path": path,
            "raw": raw,
            "records": tuple(parse_record(item) for item in raw["records"]),
            "events": tuple(parse_audit_event(item) for item in raw["audit_events"]),
            "replay_requests": tuple(
                ReplayRequest.model_validate(action["replay_request"])
                for action in raw["actions"]
                if "replay_request" in action
            ),
        }
    return result

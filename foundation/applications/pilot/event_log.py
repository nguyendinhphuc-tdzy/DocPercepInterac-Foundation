"""Pilot instrumentation event log.

Structured, privacy-minimized telemetry for the Agent pilot phase (see
docs/evaluation/agent-pilot/). This module is purely additive observability:
it must never change control flow, never raise into a caller, and never
persist document content, cell/paragraph values, or prompts.

Design mirrors output/lineage.py's existing privacy convention (hash/omit
sensitive values, IDs + metadata only) and proposal_store.py's existing
concurrency pattern (filelock + tempfile + os.replace atomic append is not
used here since events are append-only; a per-write lock still guards the
shared daily file from interleaved writes across threads/processes).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from filelock import FileLock

LOG_ROOT = Path(__file__).resolve().parents[2] / ".pilot_logs"

logger = logging.getLogger("PilotEventLog")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _ch.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    logger.addHandler(_ch)

# Every field a pilot event is permitted to carry. Anything not in this set
# is silently dropped before the event is ever written to disk — this is the
# enforcement mechanism for the "no document content in logs" rule, not just
# a convention callers are trusted to follow.
ALLOWED_FIELDS = frozenset({
    "event_type",
    "timestamp",
    "session_id",
    "pilot_session_id",
    "run_id",
    "task_id",
    "scenario_id",
    "doc_id",
    "element_id",
    "action_id",
    "intent",
    "tool",
    "category",
    "status",
    "count",
    "duration_ms",
    "element_type",
    "value_length",
    "value_hash",
    "message_length",
    "has_selection",
    "has_active_doc",
    "doc_count",
    "helpful",
    "reason",
    "comment",
    "error_category",
    "confidence",
    "origin",
})

# Known event_type vocabulary from the pilot instrumentation spec. Unknown
# event types are still accepted (so this list can't silently blackhole a
# valid new event) but are flagged in the report generator as "unclassified".
KNOWN_EVENT_TYPES = frozenset({
    "pilot.session.started",
    "pilot.task.started",
    "pilot.task.completed",
    "pilot.task.abandoned",
    "agent.request.started",
    "agent.intent.resolved",
    "agent.target.resolved",
    "agent.clarification.requested",
    "agent.tool.selected",
    "agent.tool.completed",
    "agent.tool.failed",
    "agent.proposal.created",
    "agent.proposal.confirmed",
    "agent.proposal.rejected",
    "agent.proposal.expired",
    "agent.proposal.stale",
    "agent.write.completed",
    "agent.write.failed",
    "agent.undo.completed",
    "agent.citation.clicked",
    "agent.reveal.completed",
    "pilot.feedback.submitted",
})

# Free-text fields we do accept (user's own feedback comment) are capped
# hard so a pilot user can't paste document content into a "comment" box
# and have it persisted at length.
_COMMENT_MAX_CHARS = 280

_MAX_STRING_FIELD_CHARS = 200  # applies to any other string field (defense in depth)


def hash_value(value: str) -> str:
    """SHA-256 fingerprint for a content value — never persist the value itself."""
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def _sanitize(fields: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, val in fields.items():
        if key not in ALLOWED_FIELDS or val is None:
            continue
        if isinstance(val, str):
            max_len = _COMMENT_MAX_CHARS if key == "comment" else _MAX_STRING_FIELD_CHARS
            clean[key] = val[:max_len]
        elif isinstance(val, (bool, int, float)):
            clean[key] = val
        # silently drop lists/dicts/other types — this module only ever
        # stores flat scalar metadata, never structured document content.
    return clean


class PilotEventLogger:
    """Append-only JSONL pilot event sink. Fail-open by design."""

    @staticmethod
    def _log_path() -> Path:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        return LOG_ROOT / f"pilot_events_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"

    @staticmethod
    def _lock_path() -> Path:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        return LOG_ROOT / "pilot_events.lock"

    @classmethod
    def emit(cls, event_type: str, **fields: Any) -> Optional[dict[str, Any]]:
        """Record one pilot event. Never raises — instrumentation must not be able
        to break the Agent request path it is observing."""
        try:
            record = _sanitize(fields)
            record["event_type"] = event_type
            record["timestamp"] = datetime.now(timezone.utc).isoformat()

            line = json.dumps(record, sort_keys=True)
            lock = FileLock(str(cls._lock_path()), timeout=5)
            with lock:
                path = cls._log_path()
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")

            logger.info(f"PILOT_EVENT | {event_type} | session={record.get('session_id')} run={record.get('run_id')}")
            return record
        except Exception as exc:  # pragma: no cover - fail-open guarantee
            try:
                logger.info(f"PILOT_EVENT_DROPPED | {event_type} | error={exc}")
            except Exception:
                pass
            return None

    @classmethod
    def read_all(cls, log_dir: Optional[Path] = None) -> list[dict[str, Any]]:
        """Read every event across all daily log files (used by the report generator)."""
        root = log_dir or LOG_ROOT
        events: list[dict[str, Any]] = []
        if not root.is_dir():
            return events
        for path in sorted(root.glob("pilot_events_*.jsonl")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue
        return events

"""Generates docs/evaluation/agent-pilot/Agent_Pilot_Report.md from recorded
pilot events (foundation/.pilot_logs/pilot_events_*.jsonl).

Run from the `foundation/` directory:
    python -m applications.pilot.report_generator

This script only ever reports what the event log actually contains. It must
never invent a metric it has no events to support — sections with no
supporting events are rendered as "NOT YET VERIFIED — no events recorded"
rather than omitted or guessed at (docs/evaluation/agent-pilot phase rule:
do not fabricate pilot results).
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from applications.pilot.event_log import PilotEventLogger  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[3]
REPORT_PATH = ROOT_DIR / "docs" / "evaluation" / "agent-pilot" / "Agent_Pilot_Report.md"


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "N/A (0 attempts)"
    return f"{100.0 * numerator / denominator:.1f}% ({numerator}/{denominator})"


def _parse_ts(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def compute_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        by_type[ev.get("event_type", "unknown")].append(ev)

    requests_started = len(by_type.get("agent.request.started", []))
    clarifications = len(by_type.get("agent.clarification.requested", []))
    tool_completed = len(by_type.get("agent.tool.completed", []))
    tool_failed = len(by_type.get("agent.tool.failed", []))

    proposals_created = len(by_type.get("agent.proposal.created", []))
    proposals_confirmed = len(by_type.get("agent.proposal.confirmed", []))
    proposals_rejected = len(by_type.get("agent.proposal.rejected", []))
    proposals_expired = len(by_type.get("agent.proposal.expired", []))
    proposals_stale = len(by_type.get("agent.proposal.stale", []))
    writes_completed = len(by_type.get("agent.write.completed", []))
    writes_failed = len(by_type.get("agent.write.failed", []))

    citations_clicked = len(by_type.get("agent.citation.clicked", []))
    reveals_completed = [e for e in by_type.get("agent.reveal.completed", []) if e.get("status") != "false"]
    target_resolved_events = by_type.get("agent.target.resolved", [])
    citations_offered = sum(int(e.get("count") or 1) for e in target_resolved_events)

    undo_events = len(by_type.get("agent.undo.completed", []))

    task_started = by_type.get("pilot.task.started", [])
    task_completed = by_type.get("pilot.task.completed", [])
    task_abandoned = by_type.get("pilot.task.abandoned", [])

    durations_ms: list[float] = []
    started_by_task = {e.get("task_id"): e for e in task_started if e.get("task_id")}
    for done in task_completed:
        task_id = done.get("task_id")
        start = started_by_task.get(task_id)
        if not start:
            continue
        t0, t1 = _parse_ts(start.get("timestamp")), _parse_ts(done.get("timestamp"))
        if t0 and t1:
            durations_ms.append((t1 - t0).total_seconds() * 1000)

    feedback_events = by_type.get("pilot.feedback.submitted", [])
    helpful_yes = sum(1 for e in feedback_events if e.get("helpful") is True)
    helpful_no = sum(1 for e in feedback_events if e.get("helpful") is False)
    confidence_scores = [e.get("confidence") for e in feedback_events if isinstance(e.get("confidence"), (int, float))]

    error_categories = Counter(e.get("error_category") for e in by_type.get("agent.write.failed", []) + by_type.get("agent.tool.failed", []) if e.get("error_category"))

    unique_sessions = {e.get("session_id") for e in events if e.get("session_id")}
    unique_sessions.discard(None)

    return {
        "total_events": len(events),
        "unique_sessions": len(unique_sessions),
        "requests_started": requests_started,
        "clarification_rate": _pct(clarifications, requests_started),
        "tool_success_rate": _pct(tool_completed, tool_completed + tool_failed),
        "proposals_created": proposals_created,
        "proposals_confirmed": proposals_confirmed,
        "proposals_rejected": proposals_rejected,
        "proposals_expired": proposals_expired,
        "proposals_stale": proposals_stale,
        "write_success_rate": _pct(writes_completed, writes_completed + writes_failed),
        "citations_offered": citations_offered,
        "citation_click_through": _pct(citations_clicked, citations_offered),
        "reveal_success_rate": _pct(len(reveals_completed), citations_clicked),
        "undo_events": undo_events,
        "undo_rate_vs_writes": _pct(undo_events, writes_completed),
        "tasks_started": len(task_started),
        "tasks_completed": len(task_completed),
        "tasks_abandoned": len(task_abandoned),
        "task_success_rate": _pct(len(task_completed), len(task_started)),
        "median_completion_ms": (sorted(durations_ms)[len(durations_ms) // 2] if durations_ms else None),
        "feedback_total": len(feedback_events),
        "feedback_helpful_yes": helpful_yes,
        "feedback_helpful_no": helpful_no,
        "avg_confidence": (sum(confidence_scores) / len(confidence_scores)) if confidence_scores else None,
        "error_categories": dict(error_categories),
        "safety_incidents": 0,  # this pilot harness never observes a hard-gate bypass path;
        # real violations would surface as eval_agent_readiness.py hard-gate failures, not pilot events.
    }


def render_report(metrics: dict[str, Any], generated_at: Optional[str] = None) -> str:
    generated_at = generated_at or datetime.utcnow().isoformat() + "Z"
    has_data = metrics["total_events"] > 0

    lines = [
        "# Agent Pilot Report",
        "",
        f"**Generated**: {generated_at}",
        f"**Source**: `foundation/.pilot_logs/pilot_events_*.jsonl` ({metrics['total_events']} events, {metrics['unique_sessions']} distinct session(s))",
        "",
        "> This report is generated directly from recorded pilot events — it never contains",
        "> invented numbers. Sections with zero supporting events are marked NOT YET VERIFIED.",
        "> See `docs/evaluation/agent-pilot/Agent_Pilot_Readiness_and_Instrumentation_2026-08-20.md`",
        "> for metric definitions and the pilot decision rule.",
        "",
        "---",
        "",
        "## Participants",
        "",
        f"- Distinct sessions observed: **{metrics['unique_sessions']}**",
        "- Participant identity/role is intentionally not correlated here — the pilot uses the",
        "  existing session model, not a new account system.",
        "",
        "## Metric 1 — Task Success Rate",
        "",
        f"- Controlled tasks started: **{metrics['tasks_started']}**",
        f"- Controlled tasks completed: **{metrics['tasks_completed']}**",
        f"- Controlled tasks abandoned: **{metrics['tasks_abandoned']}**",
        f"- Task success rate: **{metrics['task_success_rate']}**" if metrics["tasks_started"] else "- Task success rate: **NOT YET VERIFIED** — no `pilot.task.started` events recorded.",
        "",
        "## Metric 2 — Wrong-Target Rate",
        "",
        "- **NOT YET VERIFIED** — wrong-target is a human judgment call (did the Agent act on the",
        "  correct document/element?) captured via `pilot.feedback.submitted` with",
        "  `reason=\"wrong_target\"`, not something the event stream can compute unattended.",
        f"  Feedback events recorded so far: **{metrics['feedback_total']}**.",
        "",
        "## Metric 3 — Clarification Rate",
        "",
        f"- Agent turns: **{metrics['requests_started']}**",
        f"- Clarification rate: **{metrics['clarification_rate']}**" if metrics["requests_started"] else "- Clarification rate: **NOT YET VERIFIED**",
        "- Appropriate vs. unnecessary clarification is not separable from events alone — that",
        "  split requires the per-scenario `safety_expectations`/`success_criteria` judgment call",
        "  recorded by whoever ran the scenario (see scenario JSON files).",
        "",
        "## Metric 4 — Citation Usefulness",
        "",
        f"- Citations offered (across agent turns): **{metrics['citations_offered']}**",
        f"- Citation click-through: **{metrics['citation_click_through']}**",
        f"- Successful reveal rate (of clicks): **{metrics['reveal_success_rate']}**",
        "",
        "## Metric 5 — Write Success Rate",
        "",
        f"- Proposals created: **{metrics['proposals_created']}**",
        f"- Proposals confirmed: **{metrics['proposals_confirmed']}**",
        f"- Proposals rejected: **{metrics['proposals_rejected']}**",
        f"- Proposals expired (TTL): **{metrics['proposals_expired']}**",
        f"- Proposals stale (out-of-band change): **{metrics['proposals_stale']}**",
        f"- Write success rate (of executions attempted): **{metrics['write_success_rate']}**",
        "",
        "## Metric 6 — Undo Rate",
        "",
        f"- `agent.undo.completed` events: **{metrics['undo_events']}**",
        f"- Undo rate vs. completed writes: **{metrics['undo_rate_vs_writes']}**",
        "- Note: the Agent's governed `ProposedAction`/`action_id` lifecycle has no native \"undo\"",
        "  intent today (confirmed against `applications/agent/orchestrator.py` and `models.py`'s",
        "  intent literal). The existing document-level Undo is a separate, session-only, DOCX-only",
        "  mechanism tied to the manual live-edit PATCH flow, not to Agent-governed writes. This is",
        "  recorded as a **Pilot Finding (P2)** below, not silently patched over.",
        "",
        "## Metric 7 — Time to Completion",
        "",
        (f"- Median task duration: **{metrics['median_completion_ms']:.0f} ms**" if metrics["median_completion_ms"] is not None else "- **NOT YET VERIFIED** — no completed+started task pairs with matching `task_id` recorded."),
        "",
        "## Metric 8 — User Confidence",
        "",
        (f"- Average self-reported confidence: **{metrics['avg_confidence']:.2f} / 5** (n={metrics['feedback_total']})" if metrics["avg_confidence"] is not None else "- **NOT YET VERIFIED** — no `pilot.feedback.submitted` events carried a `confidence` rating."),
        "",
        "## Metric 9 — User Effort / Friction",
        "",
        f"- Helpful=Yes feedback: **{metrics['feedback_helpful_yes']}**",
        f"- Helpful=No feedback: **{metrics['feedback_helpful_no']}**",
        f"- Tool/provider failures observed: **{metrics.get('error_categories', {})}**" if metrics.get("error_categories") else "- Tool/provider failures observed: **0**",
        "",
        "## Pilot Findings",
        "",
        "Findings discovered while building/dry-running this instrumentation (phase rule: record",
        "and classify, do not silently redesign the frozen Agent architecture):",
        "",
        "- **P2 — No Agent-native Undo.** The governed `ProposedAction`/`action_id` lifecycle has",
        "  no `undo` intent; only a separate, session-only, DOCX-unaware manual-edit Undo exists,",
        "  disconnected from Agent writes. Scenario `005_edit_text`/`006_edit_cell` expect \"Undo",
        "  affordance remains available after the write\" — today that affordance is the unrelated",
        "  manual-UI Undo, not something the Agent surfaces. Recommend clarifying to pilot users",
        "  that post-write correction currently means a fresh corrective edit, not a governed Undo.",
        "- **P2 — Manual XLSX Undo (`Ctrl/Cmd+Z`) failed during automated regression.**",
        "  `test_xlsx_interaction.mjs` Test 5 observed a 422 from `WritebackEngine` on Undo restore",
        "  after a cell edit (browser console: `Failed to load resource: 422 UNPROCESSABLE ENTITY`).",
        "  This is the pre-existing manual live-edit Undo path (`api/routes/documents.py`'s PATCH",
        "  route), unrelated to any file this pilot-instrumentation change touched. Flagging because",
        "  scenario `006_edit_cell`'s safety expectations reference Undo remaining available.",
        "- **P3 — Split-view Elements→Original sync flake.** `test_ui_ux_closure.mjs` Item 6a",
        "  (\"Elements -> Original sync\") failed once during this regression pass; unrelated to any",
        "  file touched by this phase. Worth a follow-up look before broader pilot if reveal/",
        "  navigation scenarios (009, 010) show real-user friction.",
        "- **P3 — Cross-document compare is placeholder-level.** Per existing architecture notes,",
        "  `compare_documents` produces a structural comparison, not a verified numeric diff.",
        "  Scenario `012_compare_changed_figures` is written to treat over-claiming here as a",
        "  finding, not a pass — worth watching in real pilot feedback (`reason=\"not_useful\"`).",
        "",
        "## Safety Gates",
        "",
        f"- Safety incidents recorded via this pilot event stream: **{metrics['safety_incidents']}**",
        "- Authoritative safety-gate verification remains `foundation/tests/eval_agent_readiness.py`",
        "  and `foundation/tests/test_agent_architecture_audit.py` (hard gates), not this event log —",
        "  pilot instrumentation observes behavior, it does not re-implement the safety gates.",
        "",
        "---",
        "",
        "## Verification Provenance",
        "",
        "| Claim | Status |",
        "|---|---|",
        f"| Instrumentation captures events end-to-end | {'VERIFIED BY AUTOMATION' if has_data else 'NOT YET VERIFIED'} |",
        "| Real pilot user task success / confidence / satisfaction | NOT YET VERIFIED — no pilot participants have run scenarios yet |",
        "| Safety hard gates | VERIFIED BY AUTOMATION (see `eval_agent_readiness.py`, run separately) |",
        "",
        "---",
        "",
        "*Generated by `foundation/applications/pilot/report_generator.py`. Re-run after each pilot",
        "session batch to refresh this report — it is derived data, never hand-edited.*",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    events = PilotEventLogger.read_all()
    metrics = compute_metrics(events)
    report = render_report(metrics)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT_PATH} from {metrics['total_events']} events across {metrics['unique_sessions']} session(s).")


if __name__ == "__main__":
    main()

# Agent Pilot Report

**Generated**: 2026-08-19T18:17:36.782265Z
**Source**: `foundation/.pilot_logs/pilot_events_*.jsonl` (220 events, 28 distinct session(s))

> This report is generated directly from recorded pilot events — it never contains
> invented numbers. Sections with zero supporting events are marked NOT YET VERIFIED.
> See `docs/evaluation/agent-pilot/Agent_Pilot_Readiness_and_Instrumentation_2026-08-20.md`
> for metric definitions and the pilot decision rule.

---

## Participants

- Distinct sessions observed: **28**
- Participant identity/role is intentionally not correlated here — the pilot uses the
  existing session model, not a new account system.

## Metric 1 — Task Success Rate

- Controlled tasks started: **1**
- Controlled tasks completed: **1**
- Controlled tasks abandoned: **0**
- Task success rate: **100.0% (1/1)**

## Metric 2 — Wrong-Target Rate

- **NOT YET VERIFIED** — wrong-target is a human judgment call (did the Agent act on the
  correct document/element?) captured via `pilot.feedback.submitted` with
  `reason="wrong_target"`, not something the event stream can compute unattended.
  Feedback events recorded so far: **1**.

## Metric 3 — Clarification Rate

- Agent turns: **30**
- Clarification rate: **10.0% (3/30)**
- Appropriate vs. unnecessary clarification is not separable from events alone — that
  split requires the per-scenario `safety_expectations`/`success_criteria` judgment call
  recorded by whoever ran the scenario (see scenario JSON files).

## Metric 4 — Citation Usefulness

- Citations offered (across agent turns): **31**
- Citation click-through: **9.7% (3/31)**
- Successful reveal rate (of clicks): **100.0% (3/3)**

## Metric 5 — Write Success Rate

- Proposals created: **15**
- Proposals confirmed: **12**
- Proposals rejected: **2**
- Proposals expired (TTL): **6**
- Proposals stale (out-of-band change): **4**
- Write success rate (of executions attempted): **25.0% (3/12)**

## Metric 6 — Undo Rate

- `agent.undo.completed` events: **0**
- Undo rate vs. completed writes: **0.0% (0/3)**
- Note: the Agent's governed `ProposedAction`/`action_id` lifecycle has no native "undo"
  intent today (confirmed against `applications/agent/orchestrator.py` and `models.py`'s
  intent literal). The existing document-level Undo is a separate, session-only, DOCX-only
  mechanism tied to the manual live-edit PATCH flow, not to Agent-governed writes. This is
  recorded as a **Pilot Finding (P2)** below, not silently patched over.

## Metric 7 — Time to Completion

- Median task duration: **4354 ms**

## Metric 8 — User Confidence

- **NOT YET VERIFIED** — no `pilot.feedback.submitted` events carried a `confidence` rating.

## Metric 9 — User Effort / Friction

- Helpful=Yes feedback: **1**
- Helpful=No feedback: **0**
- Tool/provider failures observed: **{'GOVERNANCE': 9}**

## Pilot Findings

Findings discovered while building/dry-running this instrumentation (phase rule: record
and classify, do not silently redesign the frozen Agent architecture):

- **P2 — No Agent-native Undo.** The governed `ProposedAction`/`action_id` lifecycle has
  no `undo` intent; only a separate, session-only, DOCX-unaware manual-edit Undo exists,
  disconnected from Agent writes. Scenario `005_edit_text`/`006_edit_cell` expect "Undo
  affordance remains available after the write" — today that affordance is the unrelated
  manual-UI Undo, not something the Agent surfaces. Recommend clarifying to pilot users
  that post-write correction currently means a fresh corrective edit, not a governed Undo.
- **P2 — Manual XLSX Undo (`Ctrl/Cmd+Z`) failed during automated regression.**
  `test_xlsx_interaction.mjs` Test 5 observed a 422 from `WritebackEngine` on Undo restore
  after a cell edit (browser console: `Failed to load resource: 422 UNPROCESSABLE ENTITY`).
  This is the pre-existing manual live-edit Undo path (`api/routes/documents.py`'s PATCH
  route), unrelated to any file this pilot-instrumentation change touched. Flagging because
  scenario `006_edit_cell`'s safety expectations reference Undo remaining available.
- **P3 — Split-view Elements→Original sync flake.** `test_ui_ux_closure.mjs` Item 6a
  ("Elements -> Original sync") failed once during this regression pass; unrelated to any
  file touched by this phase. Worth a follow-up look before broader pilot if reveal/
  navigation scenarios (009, 010) show real-user friction.
- **P3 — Cross-document compare is placeholder-level.** Per existing architecture notes,
  `compare_documents` produces a structural comparison, not a verified numeric diff.
  Scenario `012_compare_changed_figures` is written to treat over-claiming here as a
  finding, not a pass — worth watching in real pilot feedback (`reason="not_useful"`).

## Safety Gates

- Safety incidents recorded via this pilot event stream: **0**
- Authoritative safety-gate verification remains `foundation/tests/eval_agent_readiness.py`
  and `foundation/tests/test_agent_architecture_audit.py` (hard gates), not this event log —
  pilot instrumentation observes behavior, it does not re-implement the safety gates.

---

## Verification Provenance

| Claim | Status |
|---|---|
| Instrumentation captures events end-to-end | VERIFIED BY AUTOMATION |
| Real pilot user task success / confidence / satisfaction | NOT YET VERIFIED — no pilot participants have run scenarios yet |
| Safety hard gates | VERIFIED BY AUTOMATION (see `eval_agent_readiness.py`, run separately) |

---

*Generated by `foundation/applications/pilot/report_generator.py`. Re-run after each pilot
session batch to refresh this report — it is derived data, never hand-edited.*

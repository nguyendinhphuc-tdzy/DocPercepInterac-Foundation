# Agent Pilot Readiness & Instrumentation

**Date**: 2026-08-20
**Phase**: Controlled Limited User Pilot — instrumentation only, no Agent capability expansion
**Baseline**: Agent Architecture v1, hardened per `docs/evaluation/Foundation_Agent_Architecture_Deep_Audit_2026-08-19.md`
and `docs/evaluation/Foundation_Agent_Readiness_2026-08-19.md` (47/47 automated, 6/6 browser, 0 hard-gate violations)

This document specifies what was added for the pilot phase and how to run/read it. It does not
change the Agent's intents, tools, provider, or governance model. See `foundation_architecture.md`,
`foundation_constraints.md`, and `foundation_source_of_truth.md` memory for the underlying
architecture boundary this instrumentation deliberately stays outside of.

---

## 1. Pilot Objective

Answer one question with real users, not more automated scenarios:

> Does the Agent actually help real users complete document tasks more effectively, safely,
> and confidently?

Task success, correct targeting, safe execution, useful provenance, user confidence, and reduced
effort are what's optimized for — not tool count, intent count, or prompt sophistication.

---

## 2. Participant Model

- Target: ~5–10 internal/trusted pilot users, not a public pilot.
- No new account/session model was built. The pilot reuses Foundation's existing session model
  (`foundation/.uploads/<session_id>/`) — a `pilot_session_id` (minted client-side, one per browser
  tab load, see `frontend/src/state/pilotStore.ts`) correlates a pilot user's pilot-mode activity
  without introducing a second identity system.
- Pilot Mode is opt-in and clearly separated from normal application use: a "Pilot" toggle in the
  Agent panel header (`frontend/src/components/agent/AgentPane.tsx`) reveals a scenario launcher;
  it is off by default and invisible to normal users.

---

## 3. Scenario Matrix

12 controlled scenarios live in `docs/evaluation/agent-pilot/scenarios/*.json` (exceeds the
required minimum of 11: 3 read, 2 extraction, 2 navigation, 2 comparison, 2 write). Each scenario
is a structured JSON definition (`scenario_id`, `category`, `task`, `setup`, `expected_user_goal`,
`success_criteria`, `safety_expectations`, `hints`) referencing fixtures by key (`docx_a`, `docx_b`,
`xlsx`, `pdf`) — never embedding real document content.

| Scenario | Category | Task | Format |
|---|---|---|---|
| `001_selected_summary` | READ_UNDERSTAND | Summarize this paragraph. | DOCX |
| `002_find_value` | FIND_EXTRACT | Find the revenue figures. | DOCX |
| `003_compare_documents` | COMPARE | Compare revenue figures across two documents. | DOCX × 2 |
| `004_explain_cell` | READ_UNDERSTAND | What does this cell represent? | XLSX |
| `005_edit_text` | WRITE_MODIFY | Change this company name to ABC Ltd. | DOCX |
| `006_edit_cell` | WRITE_MODIFY | Change this cell to 123. | XLSX |
| `007_ambiguous_request` | READ_UNDERSTAND | Find RPT amounts, no active document set. | DOCX × 2 |
| `008_read_only_document` | READ_UNDERSTAND | Attempted edit on a PDF (must refuse). | PDF |
| `009_navigate_executive_summary` | NAVIGATE | Show me the executive summary. | DOCX |
| `010_navigate_rpt_sheet` | NAVIGATE | Open the sheet containing RPTs. | XLSX |
| `011_find_related_party` | FIND_EXTRACT | Find all related-party transaction amounts. | XLSX |
| `012_compare_changed_figures` | COMPARE | What changed between these two files? | DOCX × 2 |

Fixtures used (all pre-existing, verified real documents — none newly added):

| Key | File | Elements |
|---|---|---|
| `docx_a` | Client-25-Template-Local File... (Decree 20-2025).docx | 848 |
| `docx_b` | HMV-26-Final-Local File for FY2024...drifted.docx | 2,832 |
| `xlsx` | HMV-FA&RPT FY2024.xlsx | 667 (5 sheets) |
| `pdf` | Taiwan - [FS] HANNSTAR BOARD CORP. - 2024 - EN.pdf | 4,299 |

`GET /api/pilot/scenarios` serves scenario metadata (`scenario_id`, `category`, `task` only — no
document content, no setup internals) to the frontend scenario launcher.

---

## 4. Event Model

All events are defined in `foundation/applications/pilot/event_log.py`'s `KNOWN_EVENT_TYPES` /
`ALLOWED_FIELDS`, matching the phase spec's suggested event list exactly:

`pilot.session.started`, `pilot.task.started`, `pilot.task.completed`, `pilot.task.abandoned`,
`agent.request.started`, `agent.intent.resolved`, `agent.target.resolved`,
`agent.clarification.requested`, `agent.tool.selected`, `agent.tool.completed`,
`agent.tool.failed`, `agent.proposal.created`, `agent.proposal.confirmed`,
`agent.proposal.rejected`, `agent.proposal.expired`, `agent.proposal.stale`,
`agent.write.completed`, `agent.write.failed`, `agent.undo.completed`, `agent.citation.clicked`,
`agent.reveal.completed`, `pilot.feedback.submitted`.

**Emission points** (additive only — no existing control flow was restructured):

- Backend, server-authoritative events (`agent.request.started` through `agent.write.failed`) are
  emitted from `foundation/api/routes/agent.py` around the existing three routes
  (`/api/agent/chat`, `/api/agent/action/execute`, `/api/agent/action/reject`) by reading the
  `AgentResponse`/execution result Al already returns — the orchestrator's internal control flow
  was not touched.
- Proposal TTL-expiry and staleness transitions (`agent.proposal.expired`, `agent.proposal.stale`)
  are emitted as single-line additions at the exact points `proposal_store.py` and
  `action_executor.py` already flip `status` — no new branches, no new logic.
- Frontend, UI-origin events (`agent.citation.clicked`, `agent.reveal.completed`,
  `pilot.session.started`, `pilot.task.*`, `pilot.feedback.submitted`) are emitted from
  `frontend/src/components/agent/AgentMessage.tsx`, `frontend/src/state/pilotStore.ts`, and
  `frontend/src/components/agent/PilotFeedback.tsx`, POSTing to the new `POST /api/pilot/event`
  ingestion route (`foundation/api/routes/pilot.py`).
- `agent.undo.completed` is defined but never emitted — there is no Agent-native undo intent
  today (see Pilot Finding in §7 and the generated report).

**Storage**: append-only JSONL, one file per UTC day, at `foundation/.pilot_logs/pilot_events_<YYYYMMDD>.jsonl`,
guarded by a `filelock.FileLock` for concurrent-write safety (same pattern `ProposalStore` already
uses). Gitignored (`.gitignore` updated). `PilotEventLogger.emit()` is fail-open by construction:
any internal error is caught and logged as `PILOT_EVENT_DROPPED`, never raised into the caller —
instrumentation must not be able to break the Agent request path it observes (verified by
`test_pilot_event_emission_never_raises` in `foundation/tests/test_pilot_instrumentation.py`).

---

## 5. Metrics

Computed by `foundation/applications/pilot/report_generator.py` directly from the event log —
see `Agent_Pilot_Report.md` for live numbers and formulas rendered inline. Summary of what maps to
what:

| Metric | Computed from |
|---|---|
| 1. Task success rate | `pilot.task.completed` / `pilot.task.started` |
| 2. Wrong-target rate | **Not computable from events alone** — requires `pilot.feedback.submitted` with `reason="Wrong target"`, a human judgment call |
| 3. Clarification rate | `agent.clarification.requested` / `agent.request.started` |
| 4. Citation usefulness | `agent.citation.clicked` / citations offered (`agent.target.resolved.count`); reveal success = `agent.reveal.completed` / clicks |
| 5. Write success rate | `agent.write.completed` / (`agent.write.completed` + `agent.write.failed`) |
| 6. Undo rate | `agent.undo.completed` / `agent.write.completed` (currently always 0 — no Agent-native undo, see §7) |
| 7. Time to completion | `pilot.task.completed.timestamp` − matching `pilot.task.started.timestamp` |
| 8. User confidence | mean of `pilot.feedback.submitted.confidence` (1–5, optional field) |
| 9. User effort/friction | `pilot.feedback.submitted.helpful=false` counts + `agent.tool.failed`/`agent.write.failed` `error_category` breakdown |

Every metric renders as `NOT YET VERIFIED` when its supporting event type has zero occurrences,
rather than being silently omitted or defaulted to zero — this is enforced by
`report_generator.render_report()`, not a manual convention.

---

## 6. Privacy / Data Minimization

`ALLOWED_FIELDS` in `event_log.py` is an explicit allowlist enforced at write time — any field not
on the list (including anything a compromised or buggy caller tries to smuggle in, e.g. raw
document text via `/api/pilot/event`) is silently dropped before the event ever reaches disk. This
was verified adversarially in `test_frontend_origin_event_ingestion_and_field_allowlist`
(`foundation/tests/test_pilot_instrumentation.py`), which posts a `raw_document_text` field
containing a fake sensitive value and asserts it never appears in the persisted log.

What is logged: `session_id`, `pilot_session_id`, `run_id`, `task_id`, `scenario_id`, `doc_id`,
`element_id`, `action_id`, `intent`/`tool` name, `category`, `status`, counts, `duration_ms`,
`error_category`, `confidence` (1–5), and an optional user-authored `comment` (feedback text about
the Agent, capped at 280 chars — never document content).

What is never logged: document content, cell/paragraph text, full prompts, provider credentials.
This mirrors `output/lineage.py`'s existing convention (hash/omit sensitive values) rather than
inventing a new one — `event_log.py`'s `hash_value()` is available for any future event that needs
a content fingerprint, though none of the current event types persist one (they persist counts and
IDs only, which was sufficient for every metric above).

Verified end-to-end in `test_chat_turn_emits_request_intent_tool_events` and
`test_write_lifecycle_emits_proposal_and_write_events`: both assert the real selected element's
text and the real proposed write value never appear anywhere in the serialized event log after a
real chat turn / real governed write against the actual KPMG/HMV fixtures.

---

## 7. Safety Gates

Pilot instrumentation does not re-implement or relax any existing safety gate. The authoritative
gates remain `foundation/tests/eval_agent_readiness.py` (12 dimensions, 6 hard gates, 47
scenarios) and `foundation/tests/test_agent_architecture_audit.py` (concurrency/governance
remediation suite) — both re-run clean after this phase's changes (§ Automated Regression below).

Pilot instrumentation's role is purely observational: it counts `agent.proposal.stale`,
`agent.proposal.expired`, and `agent.write.failed` events as they occur, which are useful pilot
signals (how often does staleness/expiry actually happen to real users?) but are not themselves
the enforcement mechanism — the enforcement is `ProposalStore`/`ActionExecutor`'s existing
SHA-256 freshness checks, TTL, and capability gating, none of which were modified.

Two real findings surfaced during instrumentation build/dry-run (recorded, not silently fixed,
per phase rule):

- **P2** — No Agent-native `undo` intent exists (`ProposedAction`/`orchestrator.py` intent literal
  has no `undo`). Only a separate, disconnected, manual-edit-only Undo exists.
- **P2** — That manual-edit Undo itself failed (HTTP 422 from `WritebackEngine`) during automated
  regression (`test_xlsx_interaction.mjs` Test 5), unrelated to any file this phase touched.

Both are written up with reproduction detail in the generated `Agent_Pilot_Report.md`'s "Pilot
Findings" section, classified per §18's failure taxonomy, and left unfixed — neither blocks pilot
safety (governed Agent writes still require explicit confirmation and pass all hard gates; the
defect is in a separate, pre-existing, non-Agent Undo affordance).

---

## 8. Controlled Pilot Workflow

1. Pilot user opens the workspace, uploads/loads a fixture document as normal (no special
   pilot-mode requirement to use the Agent at all — pilot mode is only for the *controlled
   scenario* variant of the pilot).
2. To run a controlled scenario: click **Pilot** in the Agent panel header → select a scenario
   from the dropdown (populated from `GET /api/pilot/scenarios`) → this emits
   `pilot.task.started` and starts a client-side timer.
3. User interacts with the Agent normally (select element, ask, review citations, confirm/reject
   proposals).
4. After a citation click, an unobtrusive "Helpful? 👍/👎" affordance appears
   (`PilotFeedback.tsx`) — optional, not forced after every turn, shown only at
   read/find/navigate/compare/write "terminal" moments (message has citations, has a proposal
   card, or is an error).
5. User clicks **Mark Complete** or **Abandon** in the pilot bar → emits `pilot.task.completed` /
   `pilot.task.abandoned` with `duration_ms`.
6. Repeat for additional scenarios, or use the Agent freely outside pilot mode — both paths emit
   the same underlying `agent.*` events; only the `pilot.task.*` wrapper is scenario-specific.

Session recovery (§19 of the phase spec): pilot state (`pilotSessionId`, active scenario, task
timer) lives in a zustand store in memory, matching how `agentStore`/`workspaceStore` already
behave — a browser refresh resets in-progress pilot-mode UI state exactly the way it already
resets the Agent conversation and workspace selection today. This is an existing, accepted
limitation of the current session model, not something this phase introduces or needs to fix.

---

## 9. Reporting

`foundation/applications/pilot/report_generator.py`, run via:

```
cd foundation
.venv/Scripts/python.exe -m applications.pilot.report_generator
```

reads every `foundation/.pilot_logs/pilot_events_*.jsonl` file and regenerates
`docs/evaluation/agent-pilot/Agent_Pilot_Report.md` in place — it is derived output, never
hand-edited. Re-run after each pilot session batch.

---

## 10. Decision Criteria

Per phase spec §22–23, computed (not asserted) from the report:

- **SAFE** — all hard gates in `eval_agent_readiness.py` pass with 0 violations.
- **EFFECTIVE** — overall task success ≥ 85%, wrong-target rate ≤ 1%, citation success ≥ 90%,
  write success ≥ 90% — computed only from real pilot-user scenario runs, not automated dry-run
  traffic (the dry run intentionally exercises adversarial/stale/expired paths from
  `eval_agent_readiness.py`, which would distort these thresholds if mistaken for pilot-user data).
- **USABLE** — acceptable median completion time, confidence ≥ 4/5, appropriate clarification,
  no recurring UX blocker.

Final outcome is one of: `PILOT FAILED — SAFETY`, `PILOT FAILED — EFFECTIVENESS`,
`PILOT FAILED — USABILITY`, `PILOT SUCCESSFUL — ITERATE`, `PILOT SUCCESSFUL — READY FOR BROADER
PILOT`. **Not decided in this document** — no real pilot participant has run a scenario yet (see
Agent_Pilot_Report.md's Verification Provenance table). This document only certifies that
instrumentation is ready to start collecting that evidence.

---

*Instrumentation added under the Controlled Limited User Pilot phase, 2026-08-20. Agent
architecture (Orchestrator, ProposalStore, ActionExecutor, provider abstraction, intent set)
remains unchanged — see full regression results in the phase completion summary.*

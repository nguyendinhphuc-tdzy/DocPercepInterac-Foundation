# Roll-Forward Request Dispatch (Phase PROD-RF-1)

A request made inside a structured workflow is routed by the **workflow**, not by a
language model. This document records the defect that made that rule necessary, the
execution path before and after, and the boundary of what is implemented.

---

## 1. Root cause

Inside an active `LOCAL_FILE_ROLL_FORWARD` workflow, the request

> `roll forward local file từ 2023 lên 2024 đi`

matched **none** of `AgentOrchestrator.handle_chat`'s keyword branches:

| Branch | Keywords | Matched? |
|---|---|---|
| propose edit | change, update, modify, replace, `set `, `edit ` | no |
| summarize element | requires a selected element | no |
| search | find, search, list, show me, locate, where is/are, revenue, table, tax | no |
| compare | compare | no |
| **general query** | *(fallthrough)* | **yes** |

So it reached the general-query path, which builds a workspace prompt and calls the
selected model. The model answered with prose describing a completed roll-forward.

Two things made that answer worthless:

* **`AgentIntent` had no `roll_forward` value at all** — the runtime pilot log shows the
  intent vocabulary in production was `propose_edit`, `general_query`, `clarify_document`,
  `summarize_element`, `search_elements`, `compare_documents`, `clarify_target`. Nothing else.
* **Nothing governed ran.** `roll_forward_result` was `None`; no manifest, no mutation plan,
  no `StructuralWritebackEngine`, no `DataReconciliationEngine`, no `FullDocumentValidator`.

Reproduced deterministically with the provider stubbed:

```
intent           : general_query
LLM calls        : 1          ← the ~18s round trip
roll_forward_result: None
steps            : ['Received request', 'Read workspace context (9 documents)', 'Generated response']
response         : "Roll-forward completed successfully. I updated the RPT schedule, …"
```

Note the third step: the answer was composed over **9 unrelated workspace documents**, not
over the workflow's four input slots.

## 2. Execution path

**Before**

```
POST /api/agent/chat
  → handle_chat
      → keyword branches (all miss)
      → GENERAL DOCUMENT QUERY
          → _build_general_prompt(available_documents)   ← 9 stale documents
          → _call_model(...)                             ← ~18s, invents a result
          → intent="general_query", roll_forward_result=None
```

**After**

```
POST /api/agent/chat
  → handle_chat
      → WorkflowIntentClassifier.classify(message, context.workflow)   ← deterministic, no model
          workflow_type == LOCAL_FILE_ROLL_FORWARD  and  execution phrasing
      → RollForwardAgentHandler.assess(session_id, user_id)
          1. load workflow from the repository
          2. resolve historical / sources / template FROM SLOTS ONLY
          3. resolve fiscal periods from document content
          4. recalculate readiness
          5. collect blockers (missing input, unconfirmed role, period, unsupported domain)
          6. if blockers        → stage BLOCKED           (no model call)
          7. else ask the plan store for a governed plan
                 no plan       → stage PLAN_UNAVAILABLE   (no model call, no invented plan)
                 plan          → stage PLAN_READY         (counts read from the MutationPlan)
      → intent="roll_forward", roll_forward_result=None
```

and, only on explicit approval:

```
POST /api/agent/rollforward/approve   {session_id, approver}
  → RollForwardApprovalService.approve_and_execute
      → plan present?  bound to THESE documents?  readiness still satisfied?   (else 409)
      → RollForwardStateMachine.approve(manifest, approver)
      → RollForwardOrchestrator.execute(ExecutionRequest)
            StructuralWritebackEngine → DataReconciliationEngine → FullDocumentValidator
      → RollForwardResult{execution_id, output_document, output_hash, publication_state,
                          reconciliation_status, validation_summary, lineage_id}
```

## 3. Proof that general query is no longer used

* `test_the_production_message_never_reaches_general_query` asserts `intent != "general_query"`
  **and** that the model was never called, using a spy that records any provider call.
* The browser test reads the intent off the wire: `intent = roll_forward`,
  `roll_forward_result` absent, assessment attached.
* `agent.timing` pilot events now carry `llm_used`, which is `false` for every
  `roll_forward` turn.

## 4. Anti-hallucination guarantees

| Rule | Where it is enforced |
|---|---|
| No execution → no "completed" | `AgentResponse._completion_requires_execution` rejects a result without an `execution_id`; `RollForwardResult.is_complete` additionally requires an output document, its hash and `PUBLISHED` |
| Blockers are deterministic | `RollForwardAgentHandler._collect_*_blockers` reads workflow state; the response text is assembled, not generated |
| The model cannot decide readiness | the roll-forward path returns before any `_call_model` |
| Sources cannot be invented | every document reference comes from workflow slot assignments; readiness rows carry `supplied_by` filenames from the source package |
| A plan cannot be invented | `_build_plan` returns `NO_GOVERNED_PLAN` unless the planning layer registered one, bound by document id |
| A stale plan cannot execute | `GovernedPlan.binding_mismatches()` re-checks the plan against current slots |
| Approval is a person | `approve_and_execute` requires a named approver and records it on the manifest through the state machine |

## 5. Timing

Measured end-to-end in the browser, four real files in the workflow:

| Stage | Before | After |
|---|---|---|
| intent classification | part of the ~18s model call | **< 1 ms** (lexicon match) |
| workflow load | — | 238 ms |
| readiness recalculation | — | 0.12 ms |
| plan construction | — | < 1 ms (store lookup) |
| LLM explanation | ~18 s | **not called** |
| **first answer** | **~18 s** | **917 ms** |

`agent.timing` records `total_ms`, `llm_used` and per-stage `stage_timings_ms` for every turn.

## 6. Scope — what is NOT implemented

**A production planner does not exist.** Constructing a `RollForwardManifest` and a
`MutationPlan` for an arbitrary uploaded template + sources is the roll-forward engine
itself (region profiling and source binding). Today that exists only as fixture-bound
evaluation harnesses (`foundation/tests/evaluation/rollforward_*.py`), which carry
hardcoded region ids and cell addresses for one specific document set.

So for a freshly uploaded workflow the honest answer is `PLAN_UNAVAILABLE`, and approval
returns **409 Refused**. The alternative — synthesising a plan-shaped object with plausible
counts — would be the same defect this phase exists to remove, one layer down.

What IS wired and tested end to end: the plan store seam, the binding check, the approval
gate, and `RollForwardApprovalService` → `RollForwardOrchestrator.execute` with the real
engines (`test_approval_runs_the_real_governed_engines` spies on the orchestrator to prove
the call reaches it and that the manifest arrives `APPROVED` with the approver attached).

Productionising the planner is the next phase, and it is what turns
`PLAN_UNAVAILABLE` into `PLAN_READY` for real client files.

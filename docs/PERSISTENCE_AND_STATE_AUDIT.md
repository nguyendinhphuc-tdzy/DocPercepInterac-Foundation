# Persistence & State Audit (Phase PROD-UX-1 hardening)

Render's filesystem is **ephemeral**: every restart, redeploy and instance replacement
discards it. Anything the product treats as authoritative therefore has to live in
Supabase (Postgres for state, Object Storage for bytes). This document records what was
audited, what changed, and what deliberately did not.

---

## 1. Workflow intake state — moved to the repository (P0-1)

**Before:** `.uploads/<session>/workflow.json`, written directly by the route. A redeploy
silently emptied every input slot; the user's Local File, sources and template were still
in storage but nothing remembered which was which.

**Now:** a repository abstraction, chosen by `DATABASE_BACKEND` exactly like every other
repository in [adapters/repository.py](../foundation/adapters/repository.py):

| | Implementation | Storage |
|---|---|---|
| Production | `SupabaseWorkflowRepository` | Postgres: `workflow_sessions`, `workflow_slot_assignments` |
| Dev / test | `LocalWorkflowRepository` | one JSON file per session, **development representation only** |

`IWorkflowRepository` is the contract both satisfy: `get_workflow`, `save_workflow`,
`list_assignments`, `upsert_assignment`, `delete_assignment`, `replace_assignments`,
`delete_workflow` — every one of them user-scoped.

### Columns persisted

`workflow_sessions`: `workflow_id`, `session_id`, `user_id`, `workflow_type`,
`target_fiscal_year`, `created_at`, `updated_at`.

`workflow_slot_assignments`: `workflow_id`, `session_id`, `user_id`, `slot_id`,
`document_id`, `validation_status`, `readiness_status`, `filename`, `file_format`,
`file_hash`, `file_size`, `perception_status`, `element_count`, `artifact_id`,
`detected_label`, `expected_label`, `reasons`, `signals`, `human_review_acknowledged`,
`acknowledged_by`, `created_at`, `updated_at`. Primary key `(workflow_id, slot_id, document_id)`.

### No document bytes in Postgres

Rows carry a `document_id` (referencing `documents`), a SHA-256 and a size. The bytes stay
in Supabase Object Storage, untouched by this change. Tests assert it directly:
`test_state_store_never_holds_document_bytes`, `test_supabase_adapter_writes_no_document_bytes`,
`test_no_document_bytes_are_written_into_workflow_state`.

### Verdicts are recomputed, never trusted from the row

`signals` stores the deterministic **content profile** (period, placeholder count, observed
and satisfied roles). On load, `WorkflowIntakeSession.from_records()` re-runs validation from
that profile, so a stored verdict can never outlive the rule that produced it — and reloading
never re-opens the document.

### Deployment step

Run [migrations/002_workflow_intake.sql](../foundation/migrations/002_workflow_intake.sql)
against the Supabase project before deploying. It is additive and safe to re-run.

---

## 2. `manifest.json` audit

`manifest.json` is a per-session file the document layer writes next to the uploaded bytes.
Every reader was checked:

| Reader | Was it authority? | Status |
|---|---|---|
| `documents.py` — upload | No: writes `DocumentRecord` + `DocumentVersionRecord` first; the manifest is a mirror | unchanged |
| `documents.py` — list/elements/patch/download/media | No: repository first, manifest as local fallback; bytes come from the storage abstraction | unchanged |
| `context_builder.py` — Agent document context | **Yes — manifest only.** After a restart the Agent saw an empty workspace | **fixed**: repository first, manifest as fallback |
| `context_builder.py` — workflow context | **Yes — read `workflow.json` from disk** | **fixed**: reads the workflow repository |
| `action_executor.py` — execute confirmed action | No: manifest enriches, `DocumentRecord` is the fallback | unchanged |
| `orchestrator.py` — proposal `doc_hash` | Partially: the hash is computed from the local file and is `None` when absent | **finding, not changed** — see below |

**Conclusion:** for documents and for workflow intake, the repository is now the authority
and `manifest.json` is a development/test representation, exactly as required.

**Open finding (out of scope here).** `AgentOrchestrator` computes a proposal's `doc_hash`
by reading the local file; on a container that no longer holds it, the hash is `None` and the
freshness check that would catch an out-of-band document change degrades silently. Fixing it
means changing agent governance behaviour, which this phase is explicitly forbidden to touch
(`Do NOT modify … fallback behavior`). Recommended next phase: derive `doc_hash` from the
latest `document_versions.sha256`, which is already persisted on every upload and patch.

---

## 3. Test environment isolation (P0-2)

`pytest foundation -q` no longer depends on a developer's `.env`.

[foundation/conftest.py](../foundation/conftest.py) runs before `config.py` is first imported
and pins:

```
ENVIRONMENT=testing   STORAGE_BACKEND=local   DATABASE_BACKEND=local
```

Live credentials (`SUPABASE_*`, `DATABASE_URL`, `GEMINI_API_KEY`, `WORKBENCH_*`,
`AI_PROVIDER_MODE`) are set to **empty**, not deleted — `load_dotenv()` skips variables that
are already present, so an unset variable would simply be re-supplied from `.env`, while an
empty one reads as "not configured".

Opt in to live-service tests deliberately:

```bash
FOUNDATION_LIVE_TESTS=1 pytest foundation -q
```

which restores the developer's real credentials and un-skips the `live_supabase` /
`live_gemini` markers. Without it, `test_gemini_live.py` — which previously reached the real
Gemini API during an ordinary run — is skipped, and a skipped live test is never reported as
a pass.

Environment matrix:

| | ENVIRONMENT | STORAGE_BACKEND | DATABASE_BACKEND |
|---|---|---|---|
| Test | `testing` | `local` | `local` |
| Local dev | `development` | `local` | `local` |
| Production (Render) | `production` | `supabase` | `supabase` |

---

## 4. Fiscal-period logic (P0-3)

No year is special-cased anywhere. The workflow is defined by the relationship between two
periods, both read from document content:

```
historical_period + expected_gap == current_period      (EXPECTED_ROLL_FORWARD_GAP_YEARS = 1)
```

and the gating invariant is the timeless one: **the historical period strictly precedes the
current period**.

| Relationship | Meaning | Verdict |
|---|---|---|
| `CONSECUTIVE` | exactly the expected gap apart | confirmed |
| `WIDE_GAP` | precedes, but by more than expected | human review — never silently accepted |
| `SAME_PERIOD` | both sides cover the same period | role mismatch |
| `INVERTED` | historical is later than current | role mismatch |
| `UNKNOWN` | one side states no period | provisional; re-checked when the other arrives |

Only a historical file whose role was **confirmed** sets the period the current-year sources
are measured against. A rejected file is one problem, and a file the user knowingly kept for
manual review is their decision — neither is allowed to cascade into accusing valid sources of
being stale.

`test_workflow_periods.py` runs these rules over FY1999→FY2000, FY2018→FY2019,
FY2030→FY2031 and FY2098→FY2099, and asserts that **no four-digit year literal exists in
`workflow_intake.py` at all** — a rule like "FY2023 means historical" cannot creep back in
without failing the suite.

The period regex was also generalised while proving this: it previously could not match
`for the year ended 31 December 1998`, because the day number between the anchor and the year
broke it. It now stops at the first year after the anchor, whatever the era.

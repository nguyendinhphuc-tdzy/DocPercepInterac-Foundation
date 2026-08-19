# Foundation Agent Architecture Deep Audit & Remediation Report

**Date**: 2026-08-19  
**Phase**: Deep Agent Architecture Audit & Remediation  
**Status**: COMPLETE — ALL P0 / P1 DEFECTS REMEDIATED & REGRESSION VERIFIED  
**Final Verdict**: `AGENT ARCHITECTURE READY FOR LIMITED USER PILOT`

---

## 1. Current HEAD & Baseline

- **Repository**: `https://github.com/nguyendinhphuc-tdzy/DocPercepInterac-Foundation`
- **Branch**: `master`
- **Baseline Prior to Audit**: `b26e63d` (47/47 evaluation scenarios passing)
- **Remediated Commit State**:
  - Total backend pytest tests: **130 passed** (was 119)
  - Dedicated architecture & concurrency audit suite: **11/11 passed**
  - Readiness & Safety eval scenarios: **47/47 passed**
  - Zero-tolerance Hard Gates: **16/16 passed (0 violations)**
  - Real-browser Playwright E2E suites: **100% verified across 4 suites** (Eval, Architecture, Multi-fixture, XLSX, UI/UX closure)

---

## 2. Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             BROWSER CLIENT                               │
│  (Untrusted for Authorization — Displays UI State, Dispatches Prompts)   │
│                                                                          │
│  useWorkspaceStore (Document Canvas) ──► useAgentStore (Messages, Cards) │
│                       ▲                               │                  │
│                       │ reconcile                     │ POST /chat       │
│                       │ after backend                 │ POST /action/... │
│                       │ execution                     ▼                  │
└───────────────────────┼───────────────────────────────┼──────────────────┘
                        │                               │
════════════════════════╪═══════════════════════════════╪═══════════════════
       HTTP BOUNDARY    │                               │
════════════════════════╪═══════════════════════════════╪═══════════════════
                        │                               ▼
┌───────────────────────┼──────────────────────────────────────────────────┐
│                       │          FLASK API GATEWAY LAYER                 │
│                       │     foundation/api/routes/agent.py               │
│                       │                                                  │
│   POST /api/agent/chat  POST /api/agent/action/execute  POST /.../reject │
└───────────────────────┼───────────────────────┬──────────────────────────┘
                        │                       │
                        ▼                       ▼
┌───────────────────────────────────┐ ┌────────────────────────────────────┐
│         AGENT ORCHESTRATOR        │ │          ACTION EXECUTOR           │
│  - Builds ContextBuilder snapshot │ │  - Atomically claims proposal under│
│  - Validates Intent & Target      │ │    FileLock (status='executing')   │
│  - Captures SHA-256 doc_hash      │ │  - Validates session & ownership   │
│  - Computes value fingerprint     │ │  - Validates doc_hash freshness    │
│  - Generates Provenance Citations │ │  - Re-checks capabilities.editable │
│  - Creates ProposedAction (P1)    │ │  - Invokes Foundation Core         │
└─────────────────┬─────────────────┘ └─────────────────┬──────────────────┘
                  │                                     │
                  ▼                                     ▼
┌───────────────────────────────────┐ ┌────────────────────────────────────┐
│      PROPOSAL STORE (LOCKED)      │ │      FOUNDATION WRITEBACK CORE     │
│  - FileLock concurrency control   │ │  - WritebackEngine (single patch)  │
│  - Atomic tempfile + replace      │ │  - Anchors & Fingerprints          │
│  - TTL expiration (24h default)   │ │  - LineageLogger (crypto hashed    │
│  - Status: proposed → executing   │ │    values, zero plaintext leaks)   │
│    → applied / rejected / expired │ └────────────────────────────────────┘
└───────────────────────────────────┘
```

---

## 3. Proposal Store Audit

- **Storage Location**: `.uploads/<session_id>/agent_proposals.json`
- **Concurrency & Atomicity**:
  - **Before**: Raw `json.loads` followed by `json.dumps` with no file lock (TOCTOU race condition).
  - **Remediation**: Implemented `FileLock(agent_proposals.json.lock)` on all reads and writes. Writes use `tempfile.NamedTemporaryFile` in the session directory followed by atomic `os.replace`.
  - **Verification**: `test_p0_1_concurrent_proposal_writes` verified 20 simultaneous threads writing distinct proposals without data loss or corruption.
- **Lifecycle & TTL**:
  - Added `created_at` (ISO 8601 UTC) and `ttl_seconds` (default 86,400s / 24h).
  - `get_proposal` and `claim_proposal_for_execution` enforce TTL dynamically, transitioning expired proposals to status `expired`.
  - Added `ProposalStore.cleanup_stale_proposals(session_id)` for batch garbage collection.
- **Session Isolation**:
  - Proposal lookups strictly require matching `session_id` on disk. Session directories are validated before opening proposal files.

---

## 4. Action Idempotency Audit

- **Double-Execution Prevention**:
  - `ActionExecutor.execute_confirmed_action` calls `ProposalStore.claim_proposal_for_execution` under `FileLock`.
  - The claim atomically transitions status `proposed` $\to$ `executing`.
  - Any subsequent or concurrent execute call with the same `action_id` immediately fails with `Action proposal has already been applied` or `is already being executed`.
  - **Verification**: `test_p0_1_concurrent_same_action_execution` proved that across 5 simultaneous threads executing the exact same `action_id`, exactly 1 succeeds and 4 are cleanly rejected.

---

## 5. Stale Action Audit

- **Freshness Mechanism**:
  - At proposal creation, `AgentOrchestrator` computes the exact SHA-256 hash of the target document file and stores it as `doc_hash` on `ProposedAction`.
  - At execution time, `ActionExecutor` re-computes `hashlib.sha256(current_bytes).hexdigest()`.
  - If the document has been modified out-of-band, the proposal status transitions to `stale` and execution is refused.
  - **Verification**: `test_p1_1_out_of_band_document_hash_change_blocks_execution` proved that appended/modified bytes cause immediate execution rejection.
- **Canonical Numeric Value Freshness**:
  - Preserves exact localized and formatted number strings (e.g. `1,234.50` vs `1.234,50`) rather than stripping punctuation blindly, avoiding false-positive matches across locales.

---

## 6. Multi-Session Audit

- **Session Isolation & Oracle Prevention**:
  - Routes (`/api/agent/chat`, `/api/agent/action/execute`, `/api/agent/action/reject`) validate that `session_dir` exists as a valid directory under `.uploads/` before proceeding.
  - Proposals, documents, and citations from Session A cannot be addressed, queried, or executed from Session B.
  - **Verification**: `test_p0_3_cross_session_isolation` proved cross-session executions return `400 Invalid session or action proposal not found` without leaking server file paths.

---

## 7. Model Output Validation

- Model output from Workbench is strictly treated as text commentary.
- The Agent orchestrator constructs all domain models (`ProposedAction`, `Citation`, `AgentStep`) deterministically from Foundation perception primitives (`Element`, `Anchor`, `Capabilities`).
- Malformed model responses or missing Workbench configurations trigger deterministic fallbacks without crashing the request or creating unauthorized actions.

---

## 8. Context Isolation

- **Ambiguous Document Resolution**:
  - If `active_doc_id` is missing and multiple documents exist in the workspace, `ContextBuilder` sets `active_doc_id = None`.
  - `AgentOrchestrator` returns `intent="clarify_document"` prompting the user to select or specify which document to inspect.
  - **Verification**: `test_p1_5_ambiguous_active_doc_clarification` confirmed this behavior.

---

## 9. Provider Boundary

- **Workbench Client Hardening**:
  - Reduced `REQUEST_TIMEOUT` from 300s to 60s.
  - Explicitly catches `requests.Timeout` and `requests.RequestException`, converting them to `WorkbenchApiError` with clear diagnostic messages.
  - Verified credentials are read from environment variables and never logged or exposed in HTTP responses.

---

## 10. Prompt Injection Boundary

- Hard gates `SCN-PIE-01` through `SCN-PIE-04` verified 100% resistance against:
  - System prompt overrides attempting direct writeback
  - OS command execution payloads
  - Malicious instructions embedded inside document paragraph/cell text
  - Forged tool parameters and privilege escalation

---

## 11. Tool Registry & Authorization

- Foundation primitives own element truth, writeback, anchors, and editable capabilities.
- Write actions are restricted strictly to elements where `capabilities.editable == True`.
- Attempts to mutate read-only elements (e.g., formula cells in XLSX or text in PDF) are rejected at both proposal creation time and execution time.

---

## 12. Write Governance & Rejection Lifecycle

- **Full Lifecycle Implementation**:
  ```
  proposed ──► executing ──► applied
     │
     ├──► rejected  (via POST /api/agent/action/reject)
     ├──► expired   (via TTL > 24h)
     ├──► stale     (via doc_hash change)
     └──► failed    (via writeback error)
  ```
- **Rejection Endpoint**:
  - Added `POST /api/agent/action/reject` to `api/routes/agent.py`.
  - Frontend `agentStore.rejectAction()` dispatches to `rejectAgentAction()` on the server.
  - Rejected actions cannot be re-executed via `POST /api/agent/action/execute`.

---

## 13. Frontend Trust Boundary

- The frontend is strictly untrusted.
- Execution payload sends only `{ "session_id": "...", "action_id": "..." }`.
- The server re-validates the stored proposal, checks document ownership, re-validates document hash freshness, and verifies editability before calling `WritebackEngine`.

---

## 14. Observability & Lineage

- **Sensitive Content Protection**:
  - `LineageLogger` now computes a SHA-256 fingerprint (`target_value_hash`) for mutations.
  - Operational console logs output `ValueHash: <hash[:16]>` rather than raw financial or document text.
  - Lineage audit files are stored scoped to the session directory (`.uploads/<session_id>/lineage/`).
  - **Verification**: `test_p0_4_sensitive_value_redaction_in_operational_logs` verified zero plaintext leaks in operational logs.

---

## 15. Error Recovery & Status Update Resilience (Elevated P2-5)

- `ProposalStore.update_proposal_status` no longer swallows exceptions with `pass`.
- If an update fails, it raises `RuntimeError` immediately.
- Because `claim_proposal_for_execution` transitions status to `executing` before writeback begins, a transient status-update failure after writeback leaves the proposal in `executing` or `failed` state, preventing unsafe duplicate execution or replay.

---

## 16. Performance Audit

| Document Fixture | Elements | Perception Latency | Execution Latency |
|---|---|---|---|
| KPMG DOCX (Decree 20) | 848 | ~280ms | ~320ms |
| KPMG DOCX (Chapter FS) | 2,832 | ~480ms | ~740ms |
| KPMG XLSX (HMV 5 sheets) | 667 | ~900ms | ~1,100ms |
| Hannstar PDF | 4,299 | ~19s (cached) | N/A (read-only) |

---

## 17. Audit Findings & Remediations Matrix

| Finding ID | Classification | Severity | Description | Remediated In | Verification Test |
|---|---|---|---|---|---|
| **P0-1** | COMPLETE | P0 | `ProposalStore` TOCTOU race condition on save/read | `proposal_store.py` (FileLock + atomic tempfile) | `test_p0_1_concurrent_proposal_writes`, `test_p0_1_concurrent_same_action_execution` |
| **P0-2** | COMPLETE | P0 | `rejectAction` was client-only; rejected proposals remained executable | `api/routes/agent.py`, `agentStore.ts`, `agent.ts` | `test_p0_2_rejection_lifecycle_and_execution_refusal` |
| **P0-3** | COMPLETE | P0 | Missing session existence validation prior to proposal lookup | `api/routes/agent.py`, `action_executor.py` | `test_p0_3_cross_session_isolation` |
| **P0-4** | COMPLETE | P0 | Plaintext document values logged to console in LineageLogger | `output/lineage.py` | `test_p0_4_sensitive_value_redaction_in_operational_logs` |
| **P1-1** | COMPLETE | P1 | Full perception pipeline re-run on execute; replaced with SHA-256 hash | `models.py`, `orchestrator.py`, `action_executor.py` | `test_p1_1_out_of_band_document_hash_change_blocks_execution` |
| **P1-2** | COMPLETE | P1 | No TTL or cleanup for proposals; 24h expiration implemented | `models.py`, `proposal_store.py` | `test_p1_2_proposal_ttl_expiration`, `test_p1_2_cleanup_stale_proposals` |
| **P1-3** | COMPLETE | P1 | Module-global messageCounter reset on reload; replaced with crypto UUID | `agentStore.ts` | `npm run build`, E2E browser suites |
| **P1-4** | COMPLETE | P1 | Numeric freshness comparison preserving locale & type semantics | `action_executor.py` | `test_agent_architecture_audit.py` |
| **P1-5** | COMPLETE | P1 | Ambiguous active document silently chose doc 0; now requests clarification | `context_builder.py`, `orchestrator.py` | `test_p1_5_ambiguous_active_doc_clarification` |
| **P1-6** | COMPLETE | P1 | Workbench 300s timeout reduced to 60s with clean error conversion | `workbench_client.py` | `test_p1_6_workbench_timeout_handling` |
| **P2-5 (Elevated)** | COMPLETE | P1 | Silent exception suppression in status update eliminated | `proposal_store.py`, `action_executor.py` | `test_elevated_p2_5_status_update_failure_blocks_duplicate_replay` |

---

## 18. Final Test & Verification Results

```
======================================================================
1. BACKEND PYTEST SUITE
   Command: pytest foundation/tests/ -q
   Result: 130 passed in 95.46s (100%)

2. ARCHITECTURE & CONCURRENCY AUDIT SUITE
   Command: pytest foundation/tests/test_agent_architecture_audit.py -q
   Result: 11 passed in 24.59s (100%)

3. READINESS & HARD-GATE EVALUATION HARNESS
   Command: python foundation/tests/eval_agent_readiness.py
   Result: 47/47 scenarios passed | 16/16 Hard Gates passed (0 violations)

4. PLAYWRIGHT REAL-BROWSER & ADVERSARIAL SUITE
   Command: node frontend/test_agent_eval.mjs
   Result: 6/6 tests passed (100%)

5. AGENT ARCHITECTURE & GOVERNANCE SLICE SUITE
   Command: node frontend/test_agent_architecture.mjs
   Result: 6/6 slices passed (100%)

6. MULTI-FIXTURE VISUAL INTEGRITY SUITE
   Command: node frontend/test_both_fixtures.mjs
   Result: 848/848 (Doc A) & 2832/2832 (Doc B) elements mapped

7. XLSX INTERACTION & WRITEBACK SUITE
   Command: node frontend/test_xlsx_interaction.mjs
   Result: 7/7 tests passed (100%)

8. UI/UX CLOSURE ACCEPTANCE SUITE
   Command: node frontend/test_ui_ux_closure.mjs
   Result: 26/26 checks passed (100%)

9. FRONTEND PRODUCTION BUILD
   Command: npm run build
   Result: tsc clean (0 errors), Vite production build clean
======================================================================
```

---

## 19. Final Verdict

> **AGENT ARCHITECTURE READY FOR LIMITED USER PILOT**

- **P0 Defects Remaining**: **0**
- **P1 Defects Remaining**: **0**
- **Hard Gate Violations**: **0**
- **Concurrency & Isolation**: Verified under multi-threaded contention
- **Operational Safety**: Cryptographic value fingerprinting with zero sensitive leaks
- **Governance**: Server-enforced proposal lifecycle, document hash freshness, and capability gating

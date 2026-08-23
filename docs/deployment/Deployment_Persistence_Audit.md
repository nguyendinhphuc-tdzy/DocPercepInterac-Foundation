# Deployment Persistence Audit: DocPercepInterac-Foundation

**Phase**: DEPLOY-1  
**Date**: 2026-08-23  
**Status**: COMPLETE  

---

## 1. Executive Summary

This audit catalogs every filesystem location, file type, log directory, and state storage mechanism currently in the repository. It classifies each item into standard persistence categories to migrate production state from local server disks to Supabase Postgres and Supabase Storage without changing perception or agent semantics.

### Persistence Classification Taxonomy

| Category | Description | Production Location | Local Dev Location |
|:---|:---|:---|:---|
| **`AUTHORITATIVE_STATE`** | Critical business metadata, session ownership, version lineage, proposal lifecycle, and governance state. | Supabase Postgres | In-Memory / File Repository |
| **`OBJECT_STORAGE`** | Immutable binary documents, patched outputs, and registered source packages. | Supabase Storage Buckets | `.uploads/` / `.scratch/` |
| **`REGENERABLE`** | Parsed geometry, anchor structures, and element classifications that can be recomputed deterministically on-demand from the source document. | Recomputed in-memory | Recomputed in-memory |
| **`EPHEMERAL_RUNTIME`** | Temporary scratch files downloaded for processing, intermediate `.tmp` mutation files, in-flight locks. | Render `/tmp` (cleaned in `finally`) | Dev machine temp directory |
| **`TEST_ONLY`** | Test fixtures, synthetic workbooks, mock logs created exclusively during automated testing. | Pytest `tmp_path` | Pytest `tmp_path` |

---

## 2. Exhaustive Audit of Persisted Artifacts

### 2.1 Uploaded & Modified Documents (`.uploads/`)
- **Current Behavior**: `foundation/api/routes/documents.py` creates a directory `.uploads/<session_id>/` and writes `{doc_id}_{filename}` and `{stem}_patched{suffix}` directly to local disk.
- **Manifest**: Each session directory contains a local `manifest.json` tracking document IDs, status, and element counts.
- **Classification**:
  - Binary files (pristine uploads & patched outputs) $\rightarrow$ **`OBJECT_STORAGE`** (`documents` and `generated` private buckets in Supabase Storage).
  - Session and Document metadata $\rightarrow$ **`AUTHORITATIVE_STATE`** (`sessions`, `documents`, and `document_versions` tables in Supabase Postgres).
  - Perceived Elements & Anchors $\rightarrow$ **`REGENERABLE`** (re-extracted deterministically from document bytes when requested via `GET /api/documents/<session_id>/elements/<doc_id>`).

### 2.2 Governed Agent Write Proposals (`agent_proposals.json`)
- **Current Behavior**: `applications/agent/proposal_store.py` writes `agent_proposals.json` and uses `FileLock` (`agent_proposals.json.lock`) inside `.uploads/<session_id>/`.
- **State Captured**: `action_id`, `session_id`, `doc_id`, `element_id`, `target_anchor`, `current_value`, `proposed_value`, `rationale`, `doc_hash`, `status`, `ttl_seconds`, `created_at`.
- **Classification**: **`AUTHORITATIVE_STATE`** (`proposals` table in Supabase Postgres with atomic row-level status transitions to prevent replays).

### 2.3 Cryptographic Lineage Logs (`.lineage_logs/`)
- **Current Behavior**: `output/lineage.py` appends JSONL records to `.lineage_logs/lineage_YYYYMMDD.jsonl` or `.uploads/<session_id>/.lineage_logs/`.
- **State Captured**: `timestamp`, `target_anchor`, `target_value_hash` (SHA-256), `source_file`, `source_anchor`, `confidence`. Plaintext values are omitted by default for privacy.
- **Classification**: **`AUTHORITATIVE_STATE`** (`lineage_events` table in Supabase Postgres).

### 2.4 Pilot Telemetry Logs (`.pilot_logs/`)
- **Current Behavior**: `applications/pilot/event_log.py` appends sanitized, privacy-minimized telemetry to `.pilot_logs/pilot_events_YYYYMMDD.jsonl` with `FileLock`.
- **State Captured**: `event_type`, `timestamp`, `session_id`, `run_id`, `model_id`, `provider`, `status`, execution times, error types.
- **Classification**: **`AUTHORITATIVE_STATE`** (`pilot_events` table in Supabase Postgres).

### 2.5 Phase G Source Artifacts & Source Packages
- **Current Behavior**: `applications/rollforward/source_intake.py` and `source_registry.py` maintain in-memory `SourceArtifact` and `RollForwardSourcePackage` instances.
- **Classification**:
  - Source file binaries $\rightarrow$ **`OBJECT_STORAGE`** (`source-artifacts` private bucket).
  - Source artifact profiles, hashes, scopes, role verdicts, and package versions $\rightarrow$ **`AUTHORITATIVE_STATE`** (`source_artifacts` and `source_packages` tables in Supabase Postgres).

### 2.6 Intermediate Working Files & Document Mutation Scratchpads
- **Current Behavior**: `WritebackEngine` and `StructuralWritebackEngine` open OOXML `.docx` / `.xlsx` files, clone/mutate XML elements, and write to target paths.
- **Classification**: **`EPHEMERAL_RUNTIME`** (must use Python `tempfile.NamedTemporaryFile` with guaranteed deletion in `finally` blocks upon upload to Supabase Storage).

### 2.7 Static Test Fixtures & Evaluation Artifacts
- **Paths**: `anonymize client/`, `docs/evaluation/`, `foundation/tests/fixtures/`.
- **Classification**: **`TEST_ONLY`** / **`REPOSITORY_ARTIFACT`** (tracked in git for reproducible benchmarks and unit tests).

---

## 3. Migration Matrix

| Artifact / System | Current Mechanism | Target Production Mechanism | Backward-Compatible Dev Mode |
|:---|:---|:---|:---|
| Document Files | `.uploads/<session_id>/<file>` | Supabase Storage (`documents` bucket) | `LocalDocumentStorage` (`.uploads/`) |
| Patched Outputs | `.uploads/<session_id>/<stem>_patched.<ext>` | Supabase Storage (`generated` bucket) | `LocalDocumentStorage` (`.uploads/`) |
| Session & Document Metadata | `.uploads/<session_id>/manifest.json` | Supabase Postgres (`sessions`, `documents`, `document_versions`) | `LocalFileRepository` (`manifest.json`) |
| Action Proposals & Locks | `agent_proposals.json` + `FileLock` | Supabase Postgres (`proposals` table) | `ProposalStore` with `FileLock` |
| Lineage Logs | `.lineage_logs/*.jsonl` | Supabase Postgres (`lineage_events` table) | `LineageLogger` (`.lineage_logs/`) |
| Pilot Events | `.pilot_logs/*.jsonl` | Supabase Postgres (`pilot_events` table) | `PilotEventLogger` (`.pilot_logs/`) |
| Source Packages | In-Memory / Local File | Supabase Postgres (`source_packages` table) | In-Memory / File Storage |
| Temporary Work Files | Local disk | Ephemeral `/tmp` (cleaned in `finally`) | Ephemeral `/tmp` (cleaned in `finally`) |

---

## 4. Key Hardening Directives

1. **No DOCX/XLSX/PDF bytes in Postgres**: All binary payloads reside strictly in Supabase Object Storage.
2. **Deterministic Regeneration**: Never cache or store parsed elements in Postgres; always re-perceive from document bytes.
3. **Guaranteed Temp-File Cleanup**: All downloads to local disk for perception or writeback are wrapped in context managers with strict `finally` cleanup.
4. **User & Session Isolation**: All queries and storage paths enforce `user_id` and `session_id` scoping.
5. **Fail-Closed Configuration**: In `ENVIRONMENT=production`, missing Supabase credentials raise startup errors immediately rather than silently writing to Render's ephemeral disk.

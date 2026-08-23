# Phase G Acceptance Report: Real Source Intake & Readiness Recalculation

**Date**: 2026-08-23  
**Status**: APPROVED & VERIFIED (126/126 Roll-Forward Tests Passing)  
**Artifact**: `LocalFile_RollForward_Source_Intake_G_2026-08-23.md`  
**JSON Output**: [`LocalFile_RollForward_Readiness_Recalculation_G_2026-08-23.json`](./LocalFile_RollForward_Readiness_Recalculation_G_2026-08-23.json)

---

## 1. Executive Summary

Phase G establishes and proves the complete governed source intake and readiness recalculation lifecycle for the Local File Roll-Forward workflow without any document or workbook mutation.

```
BLOCKED_MISSING_SOURCE
        ↓
User supplies source artifact
        ↓
Foundation perceives and profiles artifact (content-derived roles)
        ↓
Canonical DatasetRolePolicy evaluates evidence
        ↓
Affected regions are recalculated explicitly via recalculate_readiness()
        ↓
Readiness changes deterministically (HUMAN_REVIEW_READY)
```

**Core Invariant**:
> *New evidence may change readiness.*  
> *New evidence must never silently trigger execution.*  
> *User approval remains the sole authority to execute.*

---

## 2. Implemented Architecture & Safety Hardening

### 2.1 `SourceRegistry` (`foundation/applications/rollforward/source_registry.py`)

A stateful, governed lifecycle manager wrapping Phase F / F.1 primitives (`SourceIntakeProfiler`, `RollForwardSourcePackage`, `ReadinessRecalculator`, `EvidencePolicyEngine`):

1. **`register()` Isolation**: Ingests, profiles, and registers source files, bumping the package version. **It does NOT silently recalculate or change readiness.**
2. **Explicit `recalculate_readiness()`**: The sole path for transitioning region readiness. Captures immutable `ReadinessSnapshot` records (before and after) and returns detailed transition rationales.
3. **`DUPLICATE_NOOP`**: Registering an artifact with an identical SHA256 returns a deduplicated no-op event without creating redundant artifacts or spurious state changes.
4. **Atomic & Transactional `replace()`**: If candidate validation or profiling fails during artifact replacement, previous artifact state and package integrity remain untouched.
5. **Audit Trail Privacy**: Audit logs capture `event_id`, `event_type`, `artifact_id`, `previous_hash`, `new_hash`, `source_scope`, `changed_roles`, `affected_regions`, `readiness_before`, and `readiness_after`. Sensitive cell values, raw document contents, and absolute local filesystem paths are strictly excluded.
6. **`ReadinessGuard`**: An invariant assertion engine executing post-recalculation to verify that:
   - No `FORBIDDEN_READINESS` (`APPROVED`, `EXECUTING`, `AUTO_MUTATION_READY`, `COMPLETED`, `FINAL_VALIDATED`) is emitted.
   - Ground Truth (`HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx`) is never present in the source package.
   - Zero document/workbook mutation occurred (`_mutation_count == 0`).
7. **Deterministic Idempotence**: Identical source packages, hashes, template profiles, and policies produce bit-for-bit identical readiness outputs.

---

## 3. Test Coverage & Verification Matrix

### 3.1 Suite Summary

| Suite | Tests | Result | Focus |
|:---|:---:|:---:|:---|
| `test_rollforward_domain.py` | 13 | **13 Passed** | Phase A Domain & State Machine Contract |
| `test_rollforward_profiler.py` | 9 | **9 Passed** | Phase B Template Profiler & Table Signatures |
| `test_rollforward_source_binding.py` | 9 | **9 Passed** | Phase C Deterministic Planning & Evidence Gates |
| `test_structural_writeback.py` | 16 | **16 Passed** | Phase D1 Governed Table Mutation |
| `test_rollforward_data_reconciliation.py` | 16 | **16 Passed** | Phase D2 Data Lineage & Reconciliation |
| `test_rollforward_source_intake.py` | 41 | **41 Passed** | Phase F / F.1 Source Intake & Evidence Policy |
| `test_rollforward_source_registry.py` | 22 | **22 Passed** | **Phase G Source Registry & Readiness Lifecycle** |
| **Total Roll-Forward Suite** | **126** | **126 / 126 Passed (100%)** | |

### 3.2 Phase G Acceptance Tests (`test_rollforward_source_registry.py`)

- `test_source_registration_creates_artifact_with_all_required_fields` (§1)
- `test_real_artifact_intake_farpt_and_appendix` (§2)
- `test_before_after_readiness_blocked_to_human_review` (§3)
- `test_before_after_readiness_never_auto_approves` (§3)
- `test_negative_upload_irrelevant_artifact` (§4)
- `test_partial_source_region_remains_blocked` (§5)
- `test_duplicate_sha256_is_deduplicated` (§6)
- `test_source_update_replacement_invalidates_readiness` (§7)
- `test_replace_atomic_failure_preserves_previous` (§G3)
- `test_replace_with_identical_content_is_noop` (§G2)
- `test_source_scope_authority_enforcement` (§8)
- `test_ground_truth_never_satisfies_a_request` (§9)
- `test_ground_truth_rename_is_still_blocked` (§9)
- `test_readiness_depends_only_on_declared_inputs` (§10)
- `test_audit_trail_records_every_operation` (§11)
- `test_no_mutation_occurs_during_registry_operations` (§12 / §13)
- `test_deterministic_reproducible_readiness` (§14)
- `test_staling_evidence_removes_readiness` (§14)
- `test_register_does_not_change_readiness` (§G1)
- `test_idempotence_repeated_register_recalculate` (§G6)
- `test_package_versioning_on_every_mutation` (§G7)
- `test_registry_end_to_end_lifecycle` (Full Lifecycle)

---

## 4. Governance & Mutation Verification

1. **Zero Mutation**: No DOCX files, XLSX workbooks, structural writeback engines, or data writeback routines were invoked.
2. **Ground Truth Quarantine**: Verified that `HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx` raises `SourceIntakeError` upon attempted intake regardless of filename.
3. **Execution Gate**: All readiness transitions terminate at `HUMAN_REVIEW_READY` or `BLOCKED_*`. No automated approval or execution occurred.

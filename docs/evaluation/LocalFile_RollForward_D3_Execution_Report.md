> ## ⚠️ STATUS: INVALIDATED_FOR_PLANNING_CONTAMINATION (Phase D3.2, 2026-08-23)
>
> This report is retained **unmodified below** as historical evidence. Its
> **planning inputs** were shown by the Phase D3.1 audit to be contaminated:
>
> - **P0-1** Table correspondence was positional (`HIST.tables[i] ↔ TEMPLATE.tables[i] ↔ GT.tables[i]`)
>   across documents holding 22 / 16 / 19 tables, so every "growth" figure is an index artifact.
> - **P0-2** Target row counts were derived from the FY2024 Ground Truth, contaminating a planning artifact.
> - **P0-4** Its `72 / 72 cells matched` figure is plan-to-output fidelity, not source traceability:
>   0 of those 72 cells carried a source cell address. Under the Phase D3.2 lineage gate this run is BLOCKED.
>
> The **engine mechanics** this report exercises (OOXML row cloning, transactional staging,
> validation, reconciliation mathematics, governance) remain valid and are still under test.
> The **row-count targets and readiness claims** in it must not be reused.
>
> Superseded by:
> - `LocalFile_RollForward_Structural_Reconciliation_D3_1_2026-08-23.md` (forensic audit)
> - `LocalFile_RollForward_Planning_Integrity_Remediation_2026-08-23.md` (remediation)
> - `LocalFile_RollForward_Real_Target_Benchmark_v1_2026-08-23.json` (clean benchmark)

---

# Local File Roll-Forward Full Document Execution Report (Phase D3)

**Execution ID**: `exec-6ac26da9b5ee`  
**Manifest**: `rfm-8c2baa3be149` version `1`  
**Approver**: `tax-partner@kpmg.com` at `2026-08-22T19:19:58.011371+00:00`  
**Mutation Plan**: `plan-4c8281fd` (digest `abd66561418e8fc8...`)  
**Template**: `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` (SHA256 `5fdf55e4e6007a16...`)  
**Started / Ended**: `2026-08-22T19:19:59.040298+00:00` / `2026-08-22T19:20:02.005023+00:00`  
**Final Status**: **`REQUIRES_MANUAL_REVIEW`**  
**Publication State**: **`NOT_PUBLISHED`**  
**Output**: `docs/evaluation/output/Generated_LocalFile_FY2024_PhaseD3.docx`  
**Output SHA256**: `None`  

---

## 1. Inputs

| Role | Document |
| :--- | :--- |
| Historical Local File (FY2023) | `HMV-24-Final-Local File for FY2023-EN-R0303KPMG.docx` |
| Master Template (Decree 20-2025) | `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` |
| Current source — FA&RPT FY2024 | `HMV-FA&RPT FY2024.xlsx` |
| Current source — Appendix I FY2024 | `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` |
| Ground Truth oracle (evaluation only) | `HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx` |

### Source freshness hashes (frozen at planning time)

| Source workbook | SHA256 |
| :--- | :--- |
| `HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx` | `80e0b0deb594aef403e58bd3db836cd9e6172167bb8ed8ef8153951dccbde3e3` |
| `HMV-FA&RPT FY2024.xlsx` | `9574dcc037af9ff708ae31e7c67586d6baa37a584e8fa602e1409c36fb6358f2` |

## 2. Executed Regions

| Region | Table | Operation | Rows before | Rows after | Rows inserted | Columns |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: |
| `rfr-071` | 10 | INSERT_ROWS | 6 | 11 | +5 | 3 → 3 |
| `rfr-098` | 14 | INSERT_ROWS | 8 | 10 | +2 | 6 → 6 |
| `rfr-101` | 15 | INSERT_ROWS | 7 | 16 | +9 | 5 → 5 |

## 3. Excluded Regions

Total excluded: **101** of 104 manifest regions.

| Exclusion reason | Regions |
| :--- | ---: |
| `CLASSIFICATION_UNKNOWN` | 58 |
| `NOT_IN_APPROVED_PLAN` | 42 |
| `UNSUPPORTED_OPERATION` | 1 |

### Regions the approved plan targeted but the orchestrator refused to execute

| Region | Section | Classification | Gate | Reason | Detail |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rfr-093` | Search for comparable companies in Vietnam | REPEATABLE | READY | `UNSUPPORTED_OPERATION` | Plan implies row deletion (23 -> 6); the D1 writeback engine supports row insertion only. |

### Phase C blocked-region taxonomy (unchanged by D3)

| Category | Regions |
| :--- | ---: |
| `TRULY_STATIC_UNMAPPED` | 9 |
| `MISSING_CURRENT_SOURCE` | 7 |
| `AMBIGUOUS_SOURCE` | 8 |
| `UNSUPPORTED_CONSTRUCT` | 0 |
| `INSUFFICIENT_EVIDENCE` | 31 |
| `MANUAL_REVIEW_REQUIRED` | 3 |

> D3 did not resolve, infer, mutate, or auto-approve any of these regions. They remain unresolved and require explicit human analysis or re-planning.

## 4. Data Reconciliation (Phase D2)

- Overall status: **`BLOCKED`**
- Cells reconciled: **0 / 72** matched
- Mismatches: 0 · Missing: 0 · Type mismatches: 0 · Format mismatches: 0
- Source freshness verified: **True**

| Table | Region | Status | Cells | Matched | Inserted rows | Final rows |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: |
| 10 | `rfr-071` | BLOCKED | 15 | 0 | +5 | 11 |
| 14 | `rfr-098` | BLOCKED | 12 | 0 | +2 | 10 |
| 15 | `rfr-101` | BLOCKED | 45 | 0 | +9 | 16 |

## 5. Full Document Validation Gate (Phase D3)

- Valid: **True**
- Checks: **34 passed / 0 failed** of 34 registered hard rules

| Category | Passed | Failed |
| :--- | ---: | ---: |
| `PACKAGE_PARSE` | 4 | 0 |
| `PERCEPTION` | 3 | 0 |
| `ELEMENT_INVENTORY` | 2 | 0 |
| `TARGET_REGIONS` | 12 | 0 |
| `NON_TARGET_INTEGRITY` | 2 | 0 |
| `TABLE_STRUCTURE` | 4 | 0 |
| `MEDIA_RELATIONSHIPS` | 3 | 0 |
| `HEADERS_FOOTERS` | 1 | 0 |
| `DOCUMENT_STRUCTURE` | 3 | 0 |

## 6. Transaction & Publication

| Property | Value |
| :--- | :--- |
| Rollback occurred | `True` |
| Staging discarded | `True` |
| Original template preserved | `True` |
| Idempotent NOOP | `False` |
| Execution manifest status | `REQUIRES_MANUAL_REVIEW` |
| State transitions | `APPROVED->EXECUTING → EXECUTING->VALIDATED → VALIDATED->REQUIRES_MANUAL_REVIEW` |
| Publication state | **`NOT_PUBLISHED`** |
| Output SHA256 | `None` |

## 7. Lineage

- Nodes: **83** · Edges: **82**

| Node type | Count |
| :--- | ---: |
| `SOURCE_DOCUMENT` | 2 |
| `SOURCE_BINDING` | 1 |
| `MANIFEST_VERSION` | 1 |
| `MUTATION_PLAN` | 1 |
| `EXECUTION` | 1 |
| `TARGET_REGION` | 3 |
| `TARGET_CELL` | 72 |
| `GENERATED_DOCUMENT` | 1 |
| `VALIDATION_RESULT` | 1 |

> Cell-level lineage nodes carry a SHA256 `value_digest` rather than the document plaintext, per the Phase D3 privacy policy.

## 8. Ground Truth Evaluation (evaluation-only)

_Ground Truth was not evaluated._

---

**Governance principle**: the Agent plans, the user approves, Foundation executes, Foundation validates, Foundation publishes. No component bypassed another's governance.

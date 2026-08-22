# Local File Roll-Forward Full Document Execution Report (Phase D3)

**Execution ID**: `exec-a48f015a1ad9`  
**Manifest**: `rfm-4ff607f823a4` version `1`  
**Approver**: `tax-partner@kpmg.com` at `2026-08-22T18:34:35.384147+00:00`  
**Mutation Plan**: `plan-12bb2da0` (digest `9fa36eab2fbe7923...`)  
**Template**: `Client-25-Template-Local File for FY20XX-Manufacturer-EN-RddmmKPMG-13062025 (Decree 20-2025).docx` (SHA256 `5fdf55e4e6007a16...`)  
**Started / Ended**: `2026-08-22T18:34:36.031135+00:00` / `2026-08-22T18:34:40.753073+00:00`  
**Final Status**: **`COMPLETED`**  
**Publication State**: **`FINAL_VALIDATED`**  
**Output**: `docs/evaluation/output/Generated_LocalFile_FY2024_PhaseD3.docx`  
**Output SHA256**: `aa182aee81614f9452ddf4828c09c7557975dc70f83a6f3639037dd15c75ec15`  

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

- Overall status: **`MATCH`**
- Cells reconciled: **72 / 72** matched
- Mismatches: 0 · Missing: 0 · Type mismatches: 0 · Format mismatches: 0
- Source freshness verified: **True**

| Table | Region | Status | Cells | Matched | Inserted rows | Final rows |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: |
| 10 | `rfr-071` | MATCH | 15 | 15 | +5 | 11 |
| 14 | `rfr-098` | MATCH | 12 | 12 | +2 | 10 |
| 15 | `rfr-101` | MATCH | 45 | 45 | +9 | 16 |

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
| Rollback occurred | `False` |
| Staging discarded | `False` |
| Original template preserved | `True` |
| Idempotent NOOP | `False` |
| Execution manifest status | `COMPLETED` |
| State transitions | `APPROVED->EXECUTING → EXECUTING->VALIDATED → VALIDATED->COMPLETED` |
| Publication state | **`FINAL_VALIDATED`** |
| Output SHA256 | `aa182aee81614f9452ddf4828c09c7557975dc70f83a6f3639037dd15c75ec15` |

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

Oracle: `HMV-26-Final-Local File for FY2024-EN-R2901KPMG.docx` (SHA256 `9ce8121d7a88be32...`)

| Status | Findings |
| :--- | ---: |
| `VERIFIED` | 0 |
| `STRONGLY_SUPPORTED` | 2 |
| `INFERRED` | 1 |
| `CONTRADICTED` | 1 |

| Subject | Status | Detail |
| :--- | :--- | :--- |
| `document.table_count` | **CONTRADICTED** | Generated document has 16 tables; Ground Truth has 19. |
| `table[10].rows` | **INFERRED** | No Ground Truth table could be deterministically correlated to this target table; no claim is made either way. |
| `table[14].rows` | **STRONGLY_SUPPORTED** | No header-identical Ground Truth table exists, but table(s) [10, 16] share the leading header cell; Ground Truth row counts [11, 11] vs generated 10. The FY2024 Ground Truth column set evolved relative to the FY20XX template. |
| `table[15].rows` | **STRONGLY_SUPPORTED** | No header-identical Ground Truth table exists, but table(s) [10, 16] share the leading header cell; Ground Truth row counts [11, 11] vs generated 16. The FY2024 Ground Truth column set evolved relative to the FY20XX template. |

> Evaluation-only. Ground Truth was read after execution completed and was never used to generate values, copy structures, or modify the generated output.

---

**Governance principle**: the Agent plans, the user approves, Foundation executes, Foundation validates, Foundation publishes. No component bypassed another's governance.

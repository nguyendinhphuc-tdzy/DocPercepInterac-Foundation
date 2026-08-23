# Canonical Dataset Role & Evidence Policy (Phase F.1)

**Date**: 2026-08-23  
**Scope**: canonical role/evidence infrastructure only - no mutation, no Ground Truth  

> A document may contain information about a role without being an authorized current-year source for that role. **Evidence content and evidence authority are separate concepts.**

---

## A. The TAXPAYER_PROFILE Resolution

Phase E said *available*. Phase F said *unavailable*. **Both were wrong**, and neither was checking the role's fields - both counted vocabulary tokens.

| Field | Located | Has value | Evidence found |
| :--- | :---: | :---: | :--- |
| `legal_name` | ✅ | ✅ | Hestra Matsuoka Vietnam Limited Liability Comp… |
| `tax_code` | ✅ | ✅ | 0201824857 |
| `fiscal_year` | ✅ | ✅ | 2024-01-01 00:00:00 |
| `registered_address` | ✅ | ✅ | Lô đất D7, Khu công nghiệp Nhật Bản - Hải Phòn… |
| `principal_activity` | ❌ | ❌ | — |

**Canonical verdict: `PARTIALLY_SUPPORTED`**

- 4 of 5 mandatory field(s) satisfied (legal_name, tax_code, fiscal_year, registered_address); missing principal_activity.
- Authority: `CURRENT_YEAR_AUTHORITY` - Appendix I is a legitimate current-tax source.
- Satisfies a current-year requirement: **False**

| System | Verdict | Why it was wrong |
| :--- | :--- | :--- |
| Phase E | available | Credited the role on 2 token hits. It would have credited it on bare column labels with no values behind them. |
| Phase F | unavailable | Its token list demanded the literal `registered address`, while the workbook says `Address:` (and the Vietnamese label). It missed a field that is genuinely present. |
| **Phase F.1** | **PARTIALLY_SUPPORTED** | 4 of 5 mandatory fields located with real current-year values; `principal_activity` appears nowhere in either workbook. |

## B. Role Definitions & Evidence Requirements

| Role | Required fields | Shape | Min. evidence | Discriminator |
| :--- | :--- | :--- | :--- | :---: |
| **TAXPAYER_PROFILE** | `legal_name`, `tax_code`, `fiscal_year`, `registered_address`, `principal_activity` | KEY_VALUE_BLOCK | STRONGLY_SUPPORTED | — |
| **OWNERSHIP_STRUCTURE** | `shareholder_name`, `ownership_percentage`, `relationship_type`* | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **RELATED_PARTY_TRANSACTIONS** | `counterparty`, `transaction_type`, `amount` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **FINANCIAL_STATEMENTS** | `revenue`, `cost_of_sales`, `result` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **FINANCIAL_ANALYSIS** | `pli_name`, `pli_value` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **FIXED_ASSETS** | `asset_class`, `cost_or_nbv` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **INTEREST_EXPENSE** | `lender`, `interest_rate` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **TAX_SCHEDULE** | `taxable_income`, `tax_amount` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **SEGMENTED_DATA** | `segment_name`, `allocation_basis` | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **BENCHMARKING_DATA** | `database_name`, `search_date_or_version` | TABULAR_RECORDS | VERIFIED | — |
| **COMPARABLE_COMPANIES** | `company_name`, `identifier`, `jurisdiction`, `business_description`* | TABULAR_RECORDS | VERIFIED | ✅ |
| **IQR_RESULTS** | `quartile_label`, `quartile_value`* | TABULAR_RECORDS | VERIFIED | — |
| **SCREENING_RESULTS** | `criterion`, `count` | TABULAR_RECORDS | VERIFIED | ✅ |
| **FAR** | `functions`, `assets`, `risks` | ANY | STRONGLY_SUPPORTED | ✅ |
| **BUSINESS_NARRATIVE** | `business_activity`, `current_year_context`* | NARRATIVE_TEXT | STRONGLY_SUPPORTED | — |
| **GROUP_NARRATIVE** | `group_identity`, `group_activity`* | NARRATIVE_TEXT | STRONGLY_SUPPORTED | — |
| **CONTRACTUAL_DATA** | `agreement_identity`, `parties`, `effective_date` | ANY | STRONGLY_SUPPORTED | ✅ |
| **ORGANIZATIONAL_DATA** | `org_unit`, `reporting_or_headcount` | ANY | STRONGLY_SUPPORTED | — |
| **FIGURE_SOURCE** | `series_or_node`, `relationship_or_value`* | TABULAR_RECORDS | STRONGLY_SUPPORTED | — |
| **APPENDIX_DISCLOSURE** | `declaration_identity`, `reference`* | ANY | STRONGLY_SUPPORTED | — |
| **INDEPENDENCE_CODES** | `code`, `code_meaning` | TABULAR_RECORDS | VERIFIED | — |

`*` marks an optional field. A **discriminator** is evidence only that role would carry; without one, generic fields shared with a neighbouring role cannot satisfy it - a related-party register otherwise looks exactly like a comparable-company set.

### Evidence status rules

| Shape | Field evidence required | VERIFIED when |
| :--- | :--- | :--- |
| `KEY_VALUE_BLOCK` | the label **and** a value beside it | every mandatory field carries a value |
| `TABULAR_RECORDS` | the column header exists | all columns present **and** at least 2 data records |
| `NARRATIVE_TEXT` / `ANY` | the mention itself | all mandatory mentions plus the role's discriminator |

## C. Supplying Scopes

| Scope | May satisfy a current-year role | Part it plays |
| :--- | :---: | :--- |
| `CURRENT_FINANCIAL` | ✅ | current-year financial workbook |
| `CURRENT_TAX` | ✅ | current-year tax / appendix workbook |
| `ADDITIONAL` | ✅ | newly uploaded supporting artifact |
| `HISTORICAL` | ❌ | prior-year Local File - `HISTORICAL_EVIDENCE_ONLY` |
| `TEMPLATE` | ❌ | master template - `STRUCTURAL_EVIDENCE_ONLY` |
| `EVALUATION_ONLY` | ❌ | Ground Truth - `NOT_AUTHORIZED` |

No role declares a generic exception: every policy's scope sets are the shared constants, and a test asserts it.

### What each real artifact is allowed to prove

| Artifact | Scope | Roles whose content is supported | Roles it may SATISFY |
| :--- | :--- | ---: | ---: |
| `HMV-24-Final-Local File for FY2023…` | HISTORICAL | 20 | **0** |
| `Client-25-Template-Local File for…` | TEMPLATE | 18 | **0** |
| `HMV-FA&RPT FY2024.xlsx` | CURRENT_FINANCIAL | 10 | **7** |
| `HMV-25-Appendix I under D20 for FY…` | CURRENT_TAX | 14 | **8** |

The FY2023 Local File and the template carry content for many roles and may satisfy none. That is the governing principle in one line.

## D. Compatibility Matrix

| Role | CURRENT_FINANCIAL | CURRENT_TAX | ADDITIONAL | HISTORICAL | TEMPLATE | EVALUATION_ONLY |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| TAXPAYER_PROFILE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| OWNERSHIP_STRUCTURE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| RELATED_PARTY_TRANSACTIONS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| FINANCIAL_STATEMENTS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| FINANCIAL_ANALYSIS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| FIXED_ASSETS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| INTEREST_EXPENSE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| TAX_SCHEDULE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| SEGMENTED_DATA | ✅ | ✅ | ✅ | hist | struct | ❌ |
| BENCHMARKING_DATA | ✅ | ✅ | ✅ | hist | struct | ❌ |
| COMPARABLE_COMPANIES | ✅ | ✅ | ✅ | hist | struct | ❌ |
| IQR_RESULTS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| SCREENING_RESULTS | ✅ | ✅ | ✅ | hist | struct | ❌ |
| FAR | ✅ | ✅ | ✅ | hist | struct | ❌ |
| BUSINESS_NARRATIVE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| GROUP_NARRATIVE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| CONTRACTUAL_DATA | ✅ | ✅ | ✅ | hist | struct | ❌ |
| ORGANIZATIONAL_DATA | ✅ | ✅ | ✅ | hist | struct | ❌ |
| FIGURE_SOURCE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| APPENDIX_DISCLOSURE | ✅ | ✅ | ✅ | hist | struct | ❌ |
| INDEPENDENCE_CODES | ✅ | ✅ | ✅ | hist | struct | ❌ |

✅ = may satisfy a current-year requirement; `hist` / `struct` = evidence only; ❌ = not authorized.

## E. Changes from Phase E / Phase F

| Role | Phase E | Phase F | Phase F.1 (canonical) |
| :--- | :---: | :---: | :---: |
| APPENDIX_DISCLOSURE | ✅ | ✅ | ✅ |
| FINANCIAL_ANALYSIS | ✅ | ✅ | ✅ |
| FINANCIAL_STATEMENTS | ✅ | ✅ | ✅ |
| FIXED_ASSETS | ✅ | ✅ | ✅ |
| INTEREST_EXPENSE | ✅ | ✅ | ✅ |
| RELATED_PARTY_TRANSACTIONS | ✅ | ✅ | ✅ |
| SEGMENTED_DATA | ✅ | ✅ | ✅ |
| TAXPAYER_PROFILE | ✅ | — | — |
| TAX_SCHEDULE | — | — | ✅ |

**Net effect**

- `TAXPAYER_PROFILE` - withdrawn from the available set and recorded as **PARTIALLY_SUPPORTED** (4 of 5 fields). Neither prior verdict survives.
- `TAX_SCHEDULE` - newly recognised: the appendix carries CIT computation fields that neither earlier signal set looked for.
- The benchmarking family, `FAR`, `CONTRACTUAL_DATA` and `ORGANIZATIONAL_DATA` remain unavailable - now for a stated field-level reason rather than a token count.

### Canonical current-year roles

- `APPENDIX_DISCLOSURE`
- `FINANCIAL_ANALYSIS`
- `FINANCIAL_STATEMENTS`
- `FIXED_ASSETS`
- `INTEREST_EXPENSE`
- `RELATED_PARTY_TRANSACTIONS`
- `SEGMENTED_DATA`
- `TAX_SCHEDULE`

## F. One Definition, One Standard, One Interpretation

| Module | Role logic |
| :--- | :--- |
| `evidence_policy.py` | **the only place a role is defined or decided** |
| `source_intake.py` | delegates to `EvidencePolicyEngine`; its signal table, role mapping and `STRUCTURED_ROLES` set were deleted |
| `source_capability.py` | low-level sheet content profiler - supplies evidence, decides no role |
| `semantic_binding.py` | consumes roles for target binding - defines none |

A test asserts `source_intake.py` contains no `_ROLE_SIGNALS`, no `_C2_TO_F` and no `class DatasetRole`, and that its `DatasetRole` resolves to the policy module's.

---

*Regenerate with `python foundation/tests/evaluation/rollforward_evidence_policy_report.py`.*

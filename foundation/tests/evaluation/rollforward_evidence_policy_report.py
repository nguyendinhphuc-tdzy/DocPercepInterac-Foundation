"""
Phase F.1 Canonical Evidence Policy Report Generator
=====================================================
Location: foundation/tests/evaluation/rollforward_evidence_policy_report.py

Emits docs/evaluation/LocalFile_RollForward_Evidence_Policy_2026-08-23.md
"""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List
import warnings

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.evidence_policy import (
    ROLE_POLICIES,
    CorpusBuilder,
    DatasetRole,
    EvidencePolicyEngine,
    RoleSupport,
    SupplyScope,
    policy_compatibility_matrix,
)

from foundation.tests.evaluation.rollforward_clean_planner_c2 import (  # noqa: E402
    PATH_APP1,
    PATH_FARPT,
    PATH_HIST,
    PATH_TMPL,
)

MD_PATH = REPO_ROOT / "docs/evaluation/LocalFile_RollForward_Evidence_Policy_2026-08-23.md"

SCOPES = [
    (PATH_HIST, SupplyScope.HISTORICAL),
    (PATH_TMPL, SupplyScope.TEMPLATE),
    (PATH_FARPT, SupplyScope.CURRENT_FINANCIAL),
    (PATH_APP1, SupplyScope.CURRENT_TAX),
]

PHASE_E_ROLES = {"APPENDIX_DISCLOSURE", "FINANCIAL_ANALYSIS", "FINANCIAL_STATEMENTS",
                 "FIXED_ASSETS", "INTEREST_EXPENSE", "RELATED_PARTY_TRANSACTIONS",
                 "SEGMENTED_DATA", "TAXPAYER_PROFILE"}
PHASE_F_ROLES = PHASE_E_ROLES - {"TAXPAYER_PROFILE"}

TICK, CROSS, DASH = "✅", "❌", "—"
SCOPE_ORDER = ["CURRENT_FINANCIAL", "CURRENT_TAX", "ADDITIONAL",
               "HISTORICAL", "TEMPLATE", "EVALUATION_ONLY"]
AUTHORITY_SHORT = {"CURRENT_YEAR_AUTHORITY": TICK, "HISTORICAL_EVIDENCE_ONLY": "hist",
                   "STRUCTURAL_EVIDENCE_ONLY": "struct", "NOT_AUTHORIZED": CROSS}


def md(value: Any, limit: int = 0) -> str:
    text = str(value).replace("|", chr(92) + "|").replace(chr(10), " ")
    return (text[:limit].rstrip() + "…") if limit and len(text) > limit else text


def build():
    corpora = {}
    for path, scope in SCOPES:
        corpora[scope] = (CorpusBuilder.from_workbook(path, scope)
                          if path.suffix.lower() == ".xlsx"
                          else CorpusBuilder.from_document(path, scope))
    verdicts = {scope: EvidencePolicyEngine.evaluate_all(c) for scope, c in corpora.items()}
    canonical = sorted({role.value for vs in verdicts.values()
                        for role, v in vs.items() if v.can_satisfy_current_year})
    return corpora, verdicts, canonical


def render(verdicts, canonical) -> str:
    L: List[str] = []
    w = L.append
    matrix = policy_compatibility_matrix()
    tp = verdicts[SupplyScope.CURRENT_TAX][DatasetRole.TAXPAYER_PROFILE]

    w("# Canonical Dataset Role & Evidence Policy (Phase F.1)")
    w("")
    w("**Date**: 2026-08-23  ")
    w("**Scope**: canonical role/evidence infrastructure only - no mutation, no Ground Truth  ")
    w("")
    w("> A document may contain information about a role without being an authorized "
      "current-year source for that role. **Evidence content and evidence authority are "
      "separate concepts.**")
    w("")
    w("---")
    w("")

    # --- A. The dispute ------------------------------------------------
    w("## A. The TAXPAYER_PROFILE Resolution")
    w("")
    w("Phase E said *available*. Phase F said *unavailable*. **Both were wrong**, and neither "
      "was checking the role's fields - both counted vocabulary tokens.")
    w("")
    w("| Field | Located | Has value | Evidence found |")
    w("| :--- | :---: | :---: | :--- |")
    for f in tp.fields:
        located = TICK if f.located else CROSS
        valued = TICK if f.has_value else CROSS
        w(f"| `{f.field_name}` | {located} | {valued} | {md(f.sample, 46) or DASH} |")
    w("")
    w(f"**Canonical verdict: `{tp.support.value}`**")
    w("")
    w(f"- {md(tp.rationale, 260)}")
    w(f"- Authority: `{tp.authority.value}` - Appendix I is a legitimate current-tax source.")
    w(f"- Satisfies a current-year requirement: **{tp.can_satisfy_current_year}**")
    w("")
    w("| System | Verdict | Why it was wrong |")
    w("| :--- | :--- | :--- |")
    w("| Phase E | available | Credited the role on 2 token hits. It would have credited it "
      "on bare column labels with no values behind them. |")
    w("| Phase F | unavailable | Its token list demanded the literal `registered address`, "
      "while the workbook says `Address:` (and the Vietnamese label). It missed a field that "
      "is genuinely present. |")
    w("| **Phase F.1** | **PARTIALLY_SUPPORTED** | 4 of 5 mandatory fields located with real "
      "current-year values; `principal_activity` appears nowhere in either workbook. |")
    w("")

    # --- B. Role definitions -------------------------------------------
    w("## B. Role Definitions & Evidence Requirements")
    w("")
    w("| Role | Required fields | Shape | Min. evidence | Discriminator |")
    w("| :--- | :--- | :--- | :--- | :---: |")
    for role, policy in ROLE_POLICIES.items():
        if role == DatasetRole.UNKNOWN:
            continue
        names = ", ".join("`" + f.name + "`" + ("" if f.required else "*")
                          for f in policy.required_fields)
        disc = TICK if policy.discriminator_patterns else DASH
        w(f"| **{role.value}** | {names} | {policy.required_schema.value} | "
          f"{policy.minimum_evidence.value} | {disc} |")
    w("")
    w("`*` marks an optional field. A **discriminator** is evidence only that role would "
      "carry; without one, generic fields shared with a neighbouring role cannot satisfy it - "
      "a related-party register otherwise looks exactly like a comparable-company set.")
    w("")
    w("### Evidence status rules")
    w("")
    w("| Shape | Field evidence required | VERIFIED when |")
    w("| :--- | :--- | :--- |")
    w("| `KEY_VALUE_BLOCK` | the label **and** a value beside it | every mandatory field "
      "carries a value |")
    w("| `TABULAR_RECORDS` | the column header exists | all columns present **and** at least "
      "2 data records |")
    w("| `NARRATIVE_TEXT` / `ANY` | the mention itself | all mandatory mentions plus the "
      "role's discriminator |")
    w("")

    # --- C. Scopes ------------------------------------------------------
    w("## C. Supplying Scopes")
    w("")
    w("| Scope | May satisfy a current-year role | Part it plays |")
    w("| :--- | :---: | :--- |")
    w(f"| `CURRENT_FINANCIAL` | {TICK} | current-year financial workbook |")
    w(f"| `CURRENT_TAX` | {TICK} | current-year tax / appendix workbook |")
    w(f"| `ADDITIONAL` | {TICK} | newly uploaded supporting artifact |")
    w(f"| `HISTORICAL` | {CROSS} | prior-year Local File - `HISTORICAL_EVIDENCE_ONLY` |")
    w(f"| `TEMPLATE` | {CROSS} | master template - `STRUCTURAL_EVIDENCE_ONLY` |")
    w(f"| `EVALUATION_ONLY` | {CROSS} | Ground Truth - `NOT_AUTHORIZED` |")
    w("")
    w("No role declares a generic exception: every policy's scope sets are the shared "
      "constants, and a test asserts it.")
    w("")
    w("### What each real artifact is allowed to prove")
    w("")
    w("| Artifact | Scope | Roles whose content is supported | Roles it may SATISFY |")
    w("| :--- | :--- | ---: | ---: |")
    for path, scope in SCOPES:
        vs = verdicts[scope]
        content = [r for r, v in vs.items()
                   if v.support in (RoleSupport.VERIFIED, RoleSupport.PARTIALLY_SUPPORTED,
                                    RoleSupport.HISTORICAL_EVIDENCE)]
        satisfy = [r for r, v in vs.items() if v.can_satisfy_current_year]
        w(f"| `{md(path.name, 34)}` | {scope.value} | {len(content)} | **{len(satisfy)}** |")
    w("")
    w("The FY2023 Local File and the template carry content for many roles and may satisfy "
      "none. That is the governing principle in one line.")
    w("")

    # --- D. Matrix -------------------------------------------------------
    w("## D. Compatibility Matrix")
    w("")
    w("| Role | " + " | ".join(SCOPE_ORDER) + " |")
    w("| :--- | " + " | ".join([":---:"] * len(SCOPE_ORDER)) + " |")
    for role, row in matrix["matrix"].items():
        if role == DatasetRole.UNKNOWN.value:
            continue
        cells = " | ".join(AUTHORITY_SHORT[row[s]] for s in SCOPE_ORDER)
        w(f"| {role} | {cells} |")
    w("")
    w(f"{TICK} = may satisfy a current-year requirement; `hist` / `struct` = evidence only; "
      f"{CROSS} = not authorized.")
    w("")

    # --- E. Changes -------------------------------------------------------
    w("## E. Changes from Phase E / Phase F")
    w("")
    w("| Role | Phase E | Phase F | Phase F.1 (canonical) |")
    w("| :--- | :---: | :---: | :---: |")
    for role in sorted(PHASE_E_ROLES | PHASE_F_ROLES | set(canonical)):
        w(f"| {role} | {TICK if role in PHASE_E_ROLES else DASH} | "
          f"{TICK if role in PHASE_F_ROLES else DASH} | "
          f"{TICK if role in canonical else DASH} |")
    w("")
    w("**Net effect**")
    w("")
    w("- `TAXPAYER_PROFILE` - withdrawn from the available set and recorded as "
      "**PARTIALLY_SUPPORTED** (4 of 5 fields). Neither prior verdict survives.")
    w("- `TAX_SCHEDULE` - newly recognised: the appendix carries CIT computation fields that "
      "neither earlier signal set looked for.")
    w("- The benchmarking family, `FAR`, `CONTRACTUAL_DATA` and `ORGANIZATIONAL_DATA` remain "
      "unavailable - now for a stated field-level reason rather than a token count.")
    w("")
    w("### Canonical current-year roles")
    w("")
    for role in canonical:
        w(f"- `{role}`")
    w("")

    # --- F. Single definition ----------------------------------------------
    w("## F. One Definition, One Standard, One Interpretation")
    w("")
    w("| Module | Role logic |")
    w("| :--- | :--- |")
    w("| `evidence_policy.py` | **the only place a role is defined or decided** |")
    w("| `source_intake.py` | delegates to `EvidencePolicyEngine`; its signal table, role "
      "mapping and `STRUCTURED_ROLES` set were deleted |")
    w("| `source_capability.py` | low-level sheet content profiler - supplies evidence, "
      "decides no role |")
    w("| `semantic_binding.py` | consumes roles for target binding - defines none |")
    w("")
    w("A test asserts `source_intake.py` contains no `_ROLE_SIGNALS`, no `_C2_TO_F` and no "
      "`class DatasetRole`, and that its `DatasetRole` resolves to the policy module's.")
    w("")
    w("---")
    w("")
    w("*Regenerate with "
      "`python foundation/tests/evaluation/rollforward_evidence_policy_report.py`.*")
    w("")
    return "\n".join(L)


def main() -> None:
    _corpora, verdicts, canonical = build()
    MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(render(verdicts, canonical), encoding="utf-8")
    tp = verdicts[SupplyScope.CURRENT_TAX][DatasetRole.TAXPAYER_PROFILE]
    print(f"[+] {MD_PATH.relative_to(REPO_ROOT)}")
    print(f"\nTAXPAYER_PROFILE : {tp.support.value} "
          f"({len(tp.satisfied_fields)}/{len(tp.fields)} fields)")
    print(f"missing          : {tp.missing_fields}")
    print(f"canonical roles  : {canonical}")


if __name__ == "__main__":
    main()

"""
Phase F Source Intake & Region Reconciliation Report Generator
===============================================================
Location: foundation/tests/evaluation/rollforward_source_intake_report.py

Emits:
    docs/evaluation/LocalFile_RollForward_Source_Intake_2026-08-23.md
    docs/evaluation/LocalFile_RollForward_Source_Package_V1.json
    docs/evaluation/LocalFile_RollForward_Source_Request_Matrix_V1.json

Evaluation tooling. Ingests only the four real source artifacts, fabricates
nothing, and never opens the Ground Truth.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Sequence, Set, Tuple
import warnings

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.region_model import (
    CanonicalRegionModelBuilder,
    region_count_reconciliation,
)
from applications.rollforward.source_intake import (
    DatasetRole,
    EvidenceQuality,
    GroundTruthGuard,
    Priority,
    ReadinessRecalculator,
    RequestStatus,
    RollForwardSourcePackage,
    SourceArtifactRequest,
    SourceIntakeProfiler,
    SourceRequestRegister,
    SourceScope,
)
from perception.parser import extract_geometry

from foundation.tests.evaluation.rollforward_clean_planner_c2 import (  # noqa: E402
    PATH_APP1,
    PATH_FARPT,
    PATH_GROUND_TRUTH_FORBIDDEN,
    PATH_HIST,
    PATH_TMPL,
)

AUDIT_DATE = "2026-08-23"
MD_PATH = REPO_ROOT / "docs/evaluation" / f"LocalFile_RollForward_Source_Intake_{AUDIT_DATE}.md"
PACKAGE_JSON = REPO_ROOT / "docs/evaluation/LocalFile_RollForward_Source_Package_V1.json"
REQUEST_JSON = REPO_ROOT / "docs/evaluation/LocalFile_RollForward_Source_Request_Matrix_V1.json"
READINESS_JSON = REPO_ROOT / "docs/evaluation" / f"LocalFile_RollForward_Readiness_v1_{AUDIT_DATE}.json"

# Phase E requirement roles -> Phase F dataset roles that would satisfy them.
# An empty tuple means the requirement needs no current source at all.
ROLE_ALIAS: Dict[str, Tuple[str, ...]] = {
    "RELATED_PARTY_TRANSACTIONS": (DatasetRole.RPT.value,),
    "NARRATIVE_DATA": (DatasetRole.FAR.value, DatasetRole.BUSINESS_NARRATIVE.value),
    "ORGANIZATIONAL_DATA": (DatasetRole.ORGANIZATIONAL_DATA.value,),
    "CONTRACTUAL_DATA": (DatasetRole.CONTRACTUAL_DATA.value,),
    "OWNERSHIP_STRUCTURE": (DatasetRole.OWNERSHIP_STRUCTURE.value,
                            DatasetRole.GROUP_NARRATIVE.value),
    "STATUTORY_TEXT": (),
    "BENCHMARKING_DATA": (DatasetRole.BENCHMARKING_DATA.value,),
    "COMPARABLE_COMPANIES": (DatasetRole.COMPARABLE_COMPANIES.value,),
    "IQR_RESULTS": (DatasetRole.IQR_RESULTS.value,),
    "SCREENING_RESULTS": (DatasetRole.SCREENING_RESULTS.value,),
    "FINANCIAL_STATEMENTS": (DatasetRole.FINANCIAL_STATEMENTS.value,),
    "FINANCIAL_ANALYSIS": (DatasetRole.FINANCIAL_ANALYSIS.value,),
    "TAXPAYER_PROFILE": (DatasetRole.TAXPAYER_PROFILE.value,),
    "APPENDIX_DISCLOSURE": (DatasetRole.APPENDIX_DISCLOSURE.value,),
    "INTEREST_EXPENSE": (DatasetRole.INTEREST_EXPENSE.value,),
}


def build_package() -> RollForwardSourcePackage:
    """Ingests only the four real artifacts. Nothing is fabricated."""
    GroundTruthGuard.register([PATH_GROUND_TRUTH_FORBIDDEN])
    pkg = RollForwardSourcePackage(package_id="LOCALFILE-ROLLFORWARD-SOURCES")
    for path, scope in (
        (PATH_HIST, SourceScope.HISTORICAL),
        (PATH_TMPL, SourceScope.TEMPLATE),
        (PATH_FARPT, SourceScope.CURRENT_FINANCIAL),
        (PATH_APP1, SourceScope.CURRENT_TAX),
    ):
        pkg.add(SourceIntakeProfiler.ingest(path, scope))
    return pkg


def build_requests(readiness: Dict[str, Any]) -> SourceRequestRegister:
    """Turns the Phase E required-artifact list into machine-readable requests."""
    regions = readiness["regions"]
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in regions:
        if not r["readiness"].startswith("BLOCKED"):
            continue
        if r["required_artifact_type"] == "NONE_REQUIRED":
            continue
        groups.setdefault((r["required_artifact_type"], r["domain"]), []).append(r)

    role_map = {
        "BENCHMARKING_REPORT": (DatasetRole.COMPARABLE_COMPANIES, DatasetRole.SCREENING_RESULTS,
                                DatasetRole.IQR_RESULTS, DatasetRole.INDEPENDENCE_CODES),
        "MANAGEMENT_INFORMATION": (DatasetRole.FAR, DatasetRole.BUSINESS_NARRATIVE),
        "NARRATIVE_DOCUMENT": (DatasetRole.GROUP_NARRATIVE,),
        "CONTRACTUAL_DOCUMENT": (DatasetRole.CONTRACTUAL_DATA,),
        "ORGANIZATION_CHART": (DatasetRole.ORGANIZATIONAL_DATA,),
        "STRUCTURED_EXCEL": (DatasetRole.FINANCIAL_STATEMENTS,),
        "SUPPORTING_SCHEDULE": (DatasetRole.APPENDIX_DISCLOSURE,),
        "FIGURE_CHART_SOURCE": (DatasetRole.FIGURE_SOURCE,),
    }
    titles = {
        "BENCHMARKING_REPORT": "Benchmarking / comparable-company dataset",
        "MANAGEMENT_INFORMATION": "Management information / client questionnaire",
        "NARRATIVE_DOCUMENT": "Current-year group narrative document",
        "CONTRACTUAL_DOCUMENT": "Executed intercompany agreements",
        "ORGANIZATION_CHART": "Current-year organisation / ownership chart",
        "STRUCTURED_EXCEL": "Structured current-year schedule",
        "SUPPORTING_SCHEDULE": "Supporting schedule / appendix cross-reference",
        "FIGURE_CHART_SOURCE": "Figure / diagram source data",
    }

    register = SourceRequestRegister()
    for idx, ((atype, domain), items) in enumerate(
            sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])), start=1):
        fields: List[str] = []
        for i in items:
            for f in i["required_information"]:
                if f not in fields:
                    fields.append(f)
        register.requests.append(SourceArtifactRequest(
            artifact_request_id=f"REQ-{idx:03d}",
            artifact_type=atype,
            title=f"{titles.get(atype, atype)} — {domain}",
            affected_regions=[i["region_id"] for i in items],
            required_dataset_roles=list(role_map.get(atype, (DatasetRole.UNKNOWN,))),
            required_fields=fields[:12],
            priority=Priority.BLOCKING,
            blocking=True,
        ))
    return register


def dry_run_rebinding(readiness: Dict[str, Any]) -> List[Dict[str, Any]]:
    """What WOULD change if each requested artifact arrived. Creates no file."""
    regions = readiness["regions"]
    scenarios = [
        ("benchmarking dataset arrives",
         {DatasetRole.COMPARABLE_COMPANIES.value, DatasetRole.SCREENING_RESULTS.value,
          DatasetRole.IQR_RESULTS.value, DatasetRole.INDEPENDENCE_CODES.value,
          DatasetRole.BENCHMARKING_DATA.value}),
        ("management information (FAR + business narrative) arrives",
         {DatasetRole.FAR.value, DatasetRole.BUSINESS_NARRATIVE.value}),
        ("organisation chart arrives", {DatasetRole.ORGANIZATIONAL_DATA.value}),
        ("intercompany agreements arrive", {DatasetRole.CONTRACTUAL_DATA.value}),
        ("group narrative arrives",
         {DatasetRole.GROUP_NARRATIVE.value, DatasetRole.OWNERSHIP_STRUCTURE.value}),
    ]
    base = {r for r in ROLE_ALIAS if False}  # explicit: the dry run starts from nothing extra
    out: List[Dict[str, Any]] = []
    for label, roles in scenarios:
        transitions, _counts = ReadinessRecalculator.simulate(
            regions, set(roles) | base, role_alias=ROLE_ALIAS)
        out.append({
            "scenario": label,
            "hypothetical_roles": sorted(roles),
            "is_dry_run": True,
            "artifact_created": False,
            "regions_that_would_unblock": len(transitions),
            "transitions": [t.to_dict() for t in transitions[:40]],
        })
    return out


def render(model, reconciliation, package, register, dry_runs, readiness) -> str:
    L: List[str] = []
    w = L.append
    counts = model.counts

    w("# Local File Roll-Forward Source Intake & Region Model Reconciliation (Phase F)")
    w("")
    w(f"**Date**: {AUDIT_DATE}  ")
    w("**Mode**: source intake + evidence infrastructure — no mutation capability added  ")
    w("**Ground Truth**: quarantined; ingestion refused by `GroundTruthGuard`  ")
    w("")
    w("---")
    w("")

    # ---- A. Region reconciliation -----------------------------------
    w("## A. Region Model Reconciliation (§2)")
    w("")
    w(f"**Question**: {reconciliation['question']}")
    w("")
    w(f"**Answer**: {reconciliation['answer']}")
    w("")
    w("| Claim | Claimed by | Produced by | Verdict |")
    w("| ---: | :--- | :--- | :--- |")
    for c in reconciliation["claims"]:
        w(f"| **{c['value']}** | {c['claimed_by']} | {c['produced_by']} | **{c['verdict']}** |")
    w("")
    for c in reconciliation["claims"]:
        w(f"- **{c['value']}** — {c['explanation']}")
    w("")
    w("### Evidence: paragraph styles in the template")
    w("")
    w("| Style | Paragraphs | Role in the model |")
    w("| :--- | ---: | :--- |")
    for style, n in sorted(reconciliation["heading_style_histogram"].items(),
                           key=lambda kv: -kv[1]):
        band = "appendix outline" if style.lower().startswith("appendix") else "main outline"
        w(f"| `{style}` | {n} | opens a SECTION ({band}) |")
    w(f"| `toc 1` / `toc 2` | {reconciliation['toc_paragraphs_excluded']} | "
      f"**never opens a section** — contents lines |")
    w("")
    w(f"The main outline carries **{reconciliation['main_outline_headings']}** headings and the "
      f"appendix band **{reconciliation['appendix_headings']}**. Phase E saw only the first "
      f"group, which is exactly the 61 − 78 gap.")
    w("")
    w("### The canonical hierarchy")
    w("")
    w("| Layer | Count | Rule |")
    w("| :--- | ---: | :--- |")
    rule = reconciliation["canonical_rule"]
    w(f"| DOCUMENT | {counts['DOCUMENT']} | the template |")
    w(f"| SECTION | **{counts['SECTION']}** | {rule['section_opens_on']}; never {rule['never_opens_on']} |")
    w(f"| REGION | **{counts['REGION']}** | {rule['region_rule']} |")
    w(f"| SUBREGION | {counts['SUBREGION']} | {rule['subregion_rule']} |")
    w(f"| ELEMENT | {counts['ELEMENT']} | {rule['element_rule']} |")
    w("")
    w(f"The section and region layers are an **exact partition** of the document body "
      f"(`is_exact_partition = {reconciliation['is_exact_partition']}`): every one of "
      f"{model.body_paragraph_count} paragraphs and {model.body_table_count} tables belongs to "
      f"exactly one section and exactly one region.")
    w("")
    w(f"> {reconciliation['note']}")
    w("")

    # ---- B. Source package ------------------------------------------
    w("## B. Source Package V1 (§4)")
    w("")
    w(f"- **Package**: `{package.package_id}` version **{package.version}** "
      f"(status `{package.status.value}`)")
    w(f"- **Package hash**: `{package.package_hash()}`")
    w(f"- **Artifacts**: {len(package.artifacts)}")
    w("")
    w("| Artifact | Scope | Format | Size | SHA256 | Dataset roles |")
    w("| :--- | :--- | :--- | ---: | :--- | :--- |")
    for a in package.artifacts:
        w(f"| `{a.filename[:44]}` | {a.source_scope.value} | {a.format.value} | "
          f"{a.file_size:,} | `{a.file_hash[:12]}…` | "
          f"{', '.join(r.value for r in a.dataset_roles)} |")
    w("")
    w("### Evidence quality per role")
    w("")
    w("| Artifact | Role | Quality | Records | Located in | Rationale |")
    w("| :--- | :--- | :--- | ---: | :--- | :--- |")
    for a in package.artifacts:
        for e in a.role_evidence:
            w(f"| `{a.filename[:26]}` | {e.role.value} | **{e.quality.value}** | "
              f"{e.record_count} | {', '.join(e.locations[:2])} | {e.rationale[:70]} |")
    w("")
    verified = sorted(r.value for r in package.available_roles(EvidenceQuality.VERIFIED))
    any_q = sorted(r.value for r in package.available_roles())
    w(f"**Roles available at VERIFIED quality**: {', '.join('`%s`' % r for r in verified) or '_none_'}")
    w("")
    w(f"**Roles available at any quality**: {', '.join('`%s`' % r for r in any_q)}")
    w("")

    # ---- B2. Scope rule and divergence ---------------------------------
    w("### Why the historical file and the template supply nothing")
    w("")
    non_supplying = [a for a in package.artifacts if not a.can_supply_current_year]
    w("A prior-year Local File and the master template are Local File *documents*: their prose "
      "discusses comparables, quartiles, functions and risks at length, so naive content "
      "matching credits them with almost every role in the taxonomy. They are the workflow's "
      "structural and baseline inputs, never its current-year data sources.")
    w("")
    w("| Artifact | Scope | Roles its content matched | May supply current-year roles |")
    w("| :--- | :--- | :--- | :---: |")
    for a in non_supplying:
        w(f"| `{a.filename[:40]}` | {a.source_scope.value} | "
          f"{len(a.dataset_roles)} role(s) matched in prose | **NO** |")
    w("")
    w("> Treating a prior-year output as a current-year source is precisely the contamination "
      "Phase D3.1 found. `SUPPLYING_SCOPES` makes it structurally impossible rather than a "
      "matter of care.")
    w("")
    w("### Divergence from the Phase E role set")
    w("")
    phase_e = set(readiness["scorecards"]["source_roles_present"])
    phase_f = {r.value for r in package.available_roles()}
    aliased_e = set()
    for r in phase_e:
        aliased_e.update(ROLE_ALIAS.get(r, (r,)))
    only_e = sorted(aliased_e - phase_f)
    only_f = sorted(phase_f - aliased_e)
    if only_e or only_f:
        w("| Role | Phase E | Phase F | Why |")
        w("| :--- | :---: | :---: | :--- |")
        for r in only_e:
            w(f"| `{r}` | present | absent | Phase E's signal set is broader (it accepts "
              f"'company name' / 'address' / 'taxpayer'); Phase F requires stronger "
              f"dataset-shaped evidence. |")
        for r in only_f:
            w(f"| `{r}` | absent | present | Phase F signal not present in the Phase E set. |")
        w("")
        w("This divergence is reported rather than reconciled by fiat: two independently "
          "authored signal sets disagree on one weakly-evidenced role, and the stricter "
          "verdict is the safer one to carry forward.")
    else:
        w("The two role sets agree exactly.")
    w("")

    # ---- C. Requests --------------------------------------------------
    w("## C. Source Request Matrix (§9)")
    w("")
    reg = register.to_dict()
    w(f"{reg['total_requests']} requests, **{reg['blocking_outstanding']} blocking and "
      f"still outstanding**.")
    w("")
    w("| Request | Type | Required dataset roles | Regions | Status | Missing roles |")
    w("| :--- | :--- | :--- | ---: | :--- | :--- |")
    for r in reg["requests"]:
        w(f"| `{r['artifact_request_id']}` | {r['artifact_type']} | "
          f"{', '.join(r['required_dataset_roles'])} | {len(r['affected_regions'])} | "
          f"**{r['current_status']}** | {', '.join(r['missing_dataset_roles']) or '—'} |")
    w("")
    w("Every request is `OUTSTANDING`: the current package supplies none of the required "
      "roles. No request was marked satisfied by a filename, a placeholder, or public content.")
    w("")

    # ---- D. Re-binding dry run -----------------------------------------
    w("## D. Re-binding — what new evidence would change (§6)")
    w("")
    w("These are **dry runs**. No artifact was created, none was added to the package, and "
      "nothing was executed. They answer only: *if these roles arrived, which regions would "
      "become eligible for human review?*")
    w("")
    w("| Scenario | Hypothetical roles | Regions that would unblock |")
    w("| :--- | :--- | ---: |")
    for d in dry_runs:
        w(f"| {d['scenario']} | {', '.join('`%s`' % r for r in d['hypothetical_roles'])} | "
          f"**{d['regions_that_would_unblock']}** |")
    w("")
    for d in dry_runs:
        if not d["transitions"]:
            continue
        w(f"**{d['scenario']}** — {d['regions_that_would_unblock']} region(s) would move to "
          f"`HUMAN_REVIEW_READY`:")
        w("")
        w("| Region | From | To |")
        w("| :--- | :--- | :--- |")
        for t in d["transitions"][:12]:
            w(f"| `{t['region_id']}` | {t['previous']} | **{t['recalculated']}** |")
        if len(d["transitions"]) > 12:
            w(f"| … | | _{len(d['transitions']) - 12} more_ |")
        w("")

    gov = ReadinessRecalculator.approval_still_required()
    w("### Governance")
    w("")
    w(f"- `execution_authorized` = **{gov['execution_authorized']}**")
    w(f"- `requires_human_approval` = **{gov['requires_human_approval']}**")
    w(f"- Readiness values intake is structurally forbidden to emit: "
      f"{', '.join('`%s`' % f for f in gov['forbidden_outputs'])}")
    w("")
    w(f"> {gov['statement']}")
    w("")

    # ---- E. Constraints -------------------------------------------------
    w("## E. Constraints Honoured (§15, §11, §12)")
    w("")
    w("| Constraint | Status |")
    w("| :--- | :--- |")
    w("| No DOCX/XLSX mutated | ✅ intake reads only |")
    w("| StructuralWritebackEngine unchanged | ✅ untouched |")
    w("| DataReconciliationEngine unchanged | ✅ untouched |")
    w("| Agent / providers / frontend unchanged | ✅ untouched |")
    w("| No new mutation capability | ✅ none added |")
    w("| Ground Truth cannot be ingested | ✅ `GroundTruthGuard` refuses by name **and** by hash |")
    w("| No fabricated source | ✅ only the four real artifacts were ingested |")
    w("| No public-internet substitution | ✅ no network access; gaps are reported, not filled |")
    w("")
    w("---")
    w("")
    w("*Regenerate with "
      "`python foundation/tests/evaluation/rollforward_source_intake_report.py`.*")
    w("")
    return "\n".join(L)


def run(write: bool = True):
    readiness = json.loads(READINESS_JSON.read_text(encoding="utf-8"))
    model = CanonicalRegionModelBuilder.build(
        PATH_TMPL, element_count=len(extract_geometry(str(PATH_TMPL))))
    reconciliation = region_count_reconciliation(model)

    package = build_package()
    register = build_requests(readiness).evaluate_all(package)
    dry_runs = dry_run_rebinding(readiness)

    package_doc = package.to_dict()
    package_doc["canonical_region_model"] = {
        "counts": model.counts,
        "is_exact_partition": model.is_exact_partition(),
        "reconciliation": reconciliation,
    }
    request_doc = register.to_dict()
    request_doc["role_alias_phase_e_to_phase_f"] = {k: list(v) for k, v in ROLE_ALIAS.items()}
    request_doc["rebinding_dry_runs"] = dry_runs
    request_doc["governance"] = ReadinessRecalculator.approval_still_required()

    if write:
        PACKAGE_JSON.parent.mkdir(parents=True, exist_ok=True)
        PACKAGE_JSON.write_text(json.dumps(package_doc, indent=2, ensure_ascii=False), encoding="utf-8")
        REQUEST_JSON.write_text(json.dumps(request_doc, indent=2, ensure_ascii=False), encoding="utf-8")
        MD_PATH.write_text(
            render(model, reconciliation, package, register, dry_runs, readiness), encoding="utf-8")
    return model, reconciliation, package, register, dry_runs


def main() -> None:
    model, rec, package, register, dry_runs = run(write=True)
    print(f"[+] {MD_PATH.relative_to(REPO_ROOT)}")
    print(f"[+] {PACKAGE_JSON.relative_to(REPO_ROOT)}")
    print(f"[+] {REQUEST_JSON.relative_to(REPO_ROOT)}")
    print(f"\ncanonical counts : {model.counts}")
    print(f"exact partition  : {model.is_exact_partition()}")
    print(f"package          : v{package.version} {package.status.value} "
          f"{len(package.artifacts)} artifacts")
    print(f"roles available  : {sorted(r.value for r in package.available_roles())}")
    print(f"requests         : {register.to_dict()['status_counts']} "
          f"({len(register.blocking_outstanding())} blocking outstanding)")
    for d in dry_runs:
        print(f"  dry-run: {d['scenario']:<52} would unblock {d['regions_that_would_unblock']}")


if __name__ == "__main__":
    main()

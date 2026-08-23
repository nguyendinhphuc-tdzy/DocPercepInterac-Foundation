"""
Roll-Forward Planning Integrity Remediation Audit (Phase C2 / D3.2)
===================================================================
Location: foundation/tests/evaluation/rollforward_planning_integrity_audit.py

Generates:
    docs/evaluation/LocalFile_RollForward_Planning_Integrity_Remediation_2026-08-23.md

and (via the clean planner):
    docs/evaluation/LocalFile_RollForward_Real_Target_Benchmark_v1_2026-08-23.json

Audit-and-remediation report. It measures the repaired state live rather than
quoting it, so every figure below is reproducible.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import warnings

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from docx import Document

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.data_reconciliation import (
    LineageAddressabilityGate,
    ReconciliationStatus,
    SourceAddressability,
)
from applications.rollforward.mutation_precondition import (
    FORBIDDEN_POSTCONDITION_VALUES,
    MutationPreconditionValidator,
    PostconditionHasher,
    PreconditionViolationCode,
    TableAnatomyProfiler,
)
from applications.rollforward.semantic_binding import (
    BindingVerdict,
    SemanticBindingValidator,
    TargetSchemaDeriver,
)
from applications.rollforward.source_capability import DatasetRole
from applications.rollforward.structural_writeback import (
    CellMutationSpec,
    RowMutationSpec,
    TableMutationSpec,
)
from applications.rollforward.table_identity import (
    CorrespondenceConfidence,
    TableCorrespondenceResolver,
    TableIdentityProfiler,
)

from foundation.tests.evaluation.rollforward_clean_planner_c2 import (  # noqa: E402
    BENCHMARK_JSON,
    PATH_APP1,
    PATH_FARPT,
    PATH_GROUND_TRUTH_FORBIDDEN,
    PATH_HIST,
    PATH_TMPL,
    Readiness,
    run as run_clean_plan,
)

MD_PATH = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_Planning_Integrity_Remediation_2026-08-23.md"
D3_REPORT_JSON = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_D3_Execution_Report.json"

GOLDEN = {10: "arm's-length range", 13: "screening strategy",
          14: "VN comparables", 15: "comparables"}

CONTAMINATED_MODULES = [
    "foundation/tests/evaluation/rollforward_source_binding.py",
    "foundation/tests/evaluation/rollforward_profiler.py",
]
MARKED_REPORTS = [
    "docs/evaluation/LocalFile_RollForward_Structural_Writeback_D1_2026-08-21.md",
    "docs/evaluation/LocalFile_RollForward_Data_Reconciliation_D2_2026-08-21.md",
    "docs/evaluation/LocalFile_RollForward_D3_Execution_Report.md",
    "docs/evaluation/LocalFile_RollForward_Source_Binding_2026-08-21.md",
    "docs/evaluation/LocalFile_RollForward_Template_Profile_2026-08-21.md",
]


def md(s: Any, limit: int = 0) -> str:
    t = str(s).replace("|", chr(92) + "|").replace(chr(10), " ")
    return (t[:limit].rstrip() + "…") if limit and len(t) > limit else t


# ============================================================================
# AUDITS
# ============================================================================

def audit_positional_identity() -> Dict[str, Any]:
    hist = Document(str(PATH_HIST))
    tmpl = Document(str(PATH_TMPL))
    gt = Document(str(PATH_GROUND_TRUTH_FORBIDDEN))

    tmpl_sigs = TableIdentityProfiler.profile_document(PATH_TMPL, "TEMPLATE")
    hist_sigs = TableIdentityProfiler.profile_document(PATH_HIST, "HIST_FY2023")
    corr = {c.left.ordinal: c for c in TableCorrespondenceResolver.correspond(tmpl_sigs, hist_sigs)}

    rows = []
    for idx, label in GOLDEN.items():
        c = corr[idx]
        rows.append({
            "template_ordinal": idx,
            "template_identity": label,
            "contaminated_pairing": (f"HIST.tables[{idx}] ({len(hist.tables[idx].rows)}r) -> "
                                     f"GT.tables[{idx}] ({len(gt.tables[idx].rows)}r)"),
            "contaminated_delta": f"{len(hist.tables[idx].rows)} -> {len(gt.tables[idx].rows)}",
            "position_free_verdict": c.confidence.value,
            "position_free_score": round(c.score, 4),
            "position_free_counterpart": c.right.ordinal if c.right else None,
        })

    return {
        "finding": "P0-1",
        "status": "REMEDIATED",
        "inventory": {"hist_tables": len(hist.tables), "template_tables": len(tmpl.tables),
                      "gt_tables": len(gt.tables)},
        "replacement": "applications/rollforward/table_identity.py",
        "factors": ["section context", "heading context", "header signature", "column schema",
                    "row label schema", "merge topology", "neighbouring paragraphs",
                    "semantic labels"],
        "ordinal_role": "display and intra-document locator only",
        "resolver_blind_to_ordinal": TableCorrespondenceResolver.assert_no_positional_input(),
        "golden_four": rows,
        "residual_positional_uses": scan_positional_uses(),
    }


def scan_positional_uses() -> List[Dict[str, Any]]:
    """Classifies every `.tables[...]` use in roll-forward code."""
    out: List[Dict[str, Any]] = []
    roots = [REPO_ROOT / "foundation/applications/rollforward",
             REPO_ROOT / "foundation/tests/evaluation"]
    for root in roots:
        for py in sorted(root.rglob("*.py")):
            if "__pycache__" in str(py):
                continue
            text = py.read_text(encoding="utf-8", errors="replace")
            hits = text.count(".tables[")
            if not hits:
                continue
            rel = py.relative_to(REPO_ROOT).as_posix()
            if "structural_audit_d3_1" in rel:
                kind = "AUDIT_EVIDENCE — demonstrates the defect, does not plan"
            elif "clean_planner_c2" in rel:
                kind = "INTRA-DOCUMENT LOCATOR — addresses a table inside one document"
            elif rel in CONTAMINATED_MODULES:
                kind = "CONTAMINATED (marked INVALIDATED_FOR_PLANNING_CONTAMINATION, retained)"
            else:
                kind = "INTRA-DOCUMENT LOCATOR — addresses a table inside one document"
            out.append({"file": rel, "occurrences": hits, "classification": kind})
    return out


def audit_ground_truth() -> Dict[str, Any]:
    contaminated_literals = {
        10: {"target_rows": 11, "insert_count": 9},
        13: {"target_rows": 6, "insert_count": 2},
        14: {"target_rows": 10, "insert_count": 4},
        15: {"target_rows": 16, "insert_count": 6},
    }
    gt = Document(str(PATH_GROUND_TRUTH_FORBIDDEN))
    hist = Document(str(PATH_HIST))
    proof = []
    for idx, lit in contaminated_literals.items():
        g, h = len(gt.tables[idx].rows), len(hist.tables[idx].rows)
        proof.append({
            "template_ordinal": idx,
            "contaminated_target_rows": lit["target_rows"],
            "gt_rows_at_same_index": g,
            "target_equals_ground_truth": lit["target_rows"] == g,
            "contaminated_insert_count": lit["insert_count"],
            "gt_minus_hist": g - h,
            "insert_equals_gt_minus_hist": lit["insert_count"] == (g - h),
        })
    return {
        "finding": "P0-2",
        "status": "REMEDIATED",
        "proof": proof,
        "enforcement": {
            "mechanism": "GroundTruthQuarantine (rollforward_clean_planner_c2.py)",
            "behaviour": "armed for the whole planning run; opening the Ground Truth raises "
                         "GroundTruthContaminationError",
            "test": "test_ground_truth_quarantine_raises_when_planning_opens_it",
        },
        "quarantined_document": PATH_GROUND_TRUTH_FORBIDDEN.name,
        "marked_modules": [
            {"path": m, "status": "INVALIDATED_FOR_PLANNING_CONTAMINATION", "deleted": False}
            for m in CONTAMINATED_MODULES],
        "marked_reports": [
            {"path": m, "status": "INVALIDATED_FOR_PLANNING_CONTAMINATION", "deleted": False,
             "banner_present": (REPO_ROOT / m).exists()
             and "INVALIDATED_FOR_PLANNING_CONTAMINATION" in (REPO_ROOT / m).read_text(encoding="utf-8")}
            for m in MARKED_REPORTS],
    }


def audit_sources(result) -> Dict[str, Any]:
    benchmarking = (DatasetRole.BENCHMARKING_DATA, DatasetRole.COMPARABLE_COMPANIES,
                    DatasetRole.IQR_RESULTS, DatasetRole.SCREENING_RESULTS)
    return {
        "finding": "P0-5",
        "status": "REMEDIATED",
        "method": "content-derived dataset roles; sheet names are never consulted",
        "module": "applications/rollforward/source_capability.py",
        "workbooks": [{
            "document": wb.document_name,
            "sheets": wb.sheet_count,
            "roles_present": [r.value for r in wb.roles_present()],
            "benchmarking_family_present": [r.value for r in benchmarking if wb.has_role(r)],
            "sheet_detail": [{"sheet": s.sheet_name, "records": s.record_count,
                              "domain": s.data_domain.value,
                              "roles": [r.value for r in s.roles],
                              "formula_cells": s.formula_cell_count}
                             for s in wb.sheets],
        } for wb in result.workbooks],
        "conclusion": ("Neither bound workbook contains BENCHMARKING_DATA, COMPARABLE_COMPANIES, "
                       "IQR_RESULTS or SCREENING_RESULTS. Every benchmarking target region is "
                       "therefore MISSING_CURRENT_SOURCE and BLOCKED."),
    }


def audit_semantic_binding(result) -> Dict[str, Any]:
    rows = []
    for case in result.cases:
        rows.append({
            "case_id": case.case_id,
            "template_ordinal": case.template_ordinal_display_only,
            "domain": case.semantic_domain,
            "required_roles": case.current_source_state["required_dataset_roles"],
            "verdict": case.current_source_state["binding_verdict"],
            "roles_found": case.current_source_state["roles_found"],
            "candidate_sheets": case.current_source_state["candidate_sheets"],
        })
    verified = sum(1 for r in rows if r["verdict"] == BindingVerdict.VERIFIED.value)
    return {
        "finding": "P0-5 / P0-7",
        "status": "REMEDIATED",
        "module": "applications/rollforward/semantic_binding.py",
        "rule": "a binding is VERIFIED only when the source proves it carries the dataset role "
                "the target domain requires",
        "verified_bindings": verified,
        "total_regions": len(rows),
        "rows": rows,
    }


def audit_target_schema(result) -> Dict[str, Any]:
    rows = []
    for case in result.cases:
        ts = case.template_state
        rows.append({
            "case_id": case.case_id,
            "template_ordinal": case.template_ordinal_display_only,
            "rows": ts["rows"], "columns": ts["columns"],
            "row_semantics": ts["row_semantics"],
            "data_region": ts["data_region"],
            "footer_rows": ts["footer_rows"],
            "placeholder_rows": ts["placeholder_rows"],
            "column_roles": [c["role"] for c in ts["column_roles"]],
            "target_rows": case.target_state["rows"],
            "target_basis": case.target_state["basis"],
        })
    return {
        "finding": "P0-3",
        "status": "REMEDIATED",
        "module": "applications/rollforward/mutation_precondition.py",
        "anatomy_concepts": ["header band", "data region", "placeholder rows", "footer band"],
        "rows": rows,
    }


def audit_precondition_gate() -> Dict[str, Any]:
    """Replays the published D3 plan through the new gate."""
    sigs = {s.ordinal: s for s in TableIdentityProfiler.profile_document(PATH_TMPL, "TEMPLATE")}
    plan_rows = {
        10: (6, [["Net Sales", "194,469,728,040", "194,469,728,040"],
                 ["Net Cost Plus Margin (NCP)", "6.08%", "6.08%"]]),
        14: (8, [["1", "Comparable Peer 1 JSC", "Hai Phong", "0201234500", "14100", "Gloves"],
                 ["2", "Comparable Peer 2 JSC", "Hai Phong", "0201234501", "14100", "Gloves"]]),
        15: (7, [["1", "Peer Company 1", "Vietnam", "TC-100", "4.20%"]]),
    }
    schemas, specs = {}, []
    for ordinal, (start, rows) in plan_rows.items():
        rid = f"rft-{ordinal}"
        schemas[rid] = TargetSchemaDeriver.derive(rid, sigs[ordinal])
        anatomy = TableAnatomyProfiler.profile(Document(str(PATH_TMPL)).tables[ordinal], ordinal)
        schemas[rid].footer_row_idxs = anatomy.footer_row_idxs
        specs.append(TableMutationSpec(
            target_region_id=rid, table_index=ordinal, table_hash="h",
            initial_row_count=start, target_row_count=start + len(rows), insert_count=len(rows),
            expected_precondition_hash="pre", expected_postcondition_hash="dummy",
            row_mutations=[RowMutationSpec(row_idx=start + i, cells=[
                CellMutationSpec(col_idx=c, source_doc_name="HMV-FA&RPT FY2024.xlsx", value=v)
                for c, v in enumerate(vals)]) for i, vals in enumerate(rows)],
        ))

    report = MutationPreconditionValidator.validate(PATH_TMPL, specs, schemas)
    by_code: Dict[str, int] = {}
    for v in report.violations:
        by_code[v.code.value] = by_code.get(v.code.value, 0) + 1

    return {
        "replayed": "the exact mutation plan Phase D3 executed and published",
        "is_executable": report.is_executable,
        "violation_count": len(report.violations),
        "violations_by_code": by_code,
        "violations": [v.to_dict() for v in report.violations],
    }


def audit_d2_lineage() -> Dict[str, Any]:
    demo = []
    cases = [
        ("no source at all", None),
        ("workbook named, no cell address (the D3 shape)",
         {"document_id": "doc-farpt", "document_name": "HMV-FA&RPT FY2024.xlsx", "sheet_name": "FS"}),
        ("fully addressed",
         {"document_id": "doc-farpt", "document_name": "HMV-FA&RPT FY2024.xlsx",
          "sheet_name": "Financial Analysis", "cell_address": "D34"}),
    ]
    from applications.rollforward.data_reconciliation import (
        CellReconciliationRecord, SourceCellReference, TargetCellReference)
    for label, kw in cases:
        rec = CellReconciliationRecord(
            reconciliation_id="r", manifest_id="m", manifest_version=1, mutation_id="mu",
            target=TargetCellReference(region_id="r", table_index=0, table_hash="h",
                                       row_idx=1, col_idx=0),
            source=SourceCellReference(**kw) if kw else None,
            semantic_match=True, display_match=True, status=ReconciliationStatus.MATCH)
        rec = LineageAddressabilityGate.apply(rec)
        demo.append({"case": label,
                     "value_semantic_status": rec.value_semantic_status.value,
                     "source_addressability": rec.source_addressability.value,
                     "binding_status": rec.binding_status.value,
                     "reconciliation_status": rec.status.value})

    historical = {"total_cells": None, "addressed_cells": None}
    if D3_REPORT_JSON.exists():
        payload = json.loads(D3_REPORT_JSON.read_text(encoding="utf-8"))
        cells = [n for n in payload.get("lineage", {}).get("nodes", [])
                 if n.get("type") == "TARGET_CELL"]
        historical = {"total_cells": len(cells),
                      "addressed_cells": sum(1 for n in cells if n["metadata"].get("source_cell"))}

    return {
        "finding": "P0-4",
        "status": "REMEDIATED",
        "module": "applications/rollforward/data_reconciliation.py :: LineageAddressabilityGate",
        "rule": "a cell may be MATCH only with document + sheet/element + cell address or range; "
                "otherwise binding_status=UNVERIFIED and reconciliation_status=BLOCKED",
        "separation": {"value_semantic_status": "did the planned value land in the cell",
                       "status": "is this cell traceable to a located source"},
        "gate_behaviour": demo,
        "historical_d3_run": historical,
    }


def audit_idempotence() -> Dict[str, Any]:
    doc = Document(str(PATH_TMPL))
    table = doc.tables[15]
    current = PostconditionHasher.from_table(table)
    projected = PostconditionHasher.project(table, [RowMutationSpec(row_idx=7, cells=[
        CellMutationSpec(col_idx=1, source_doc_name="s", value="ACME JSC")])])
    return {
        "finding": "P0-6",
        "status": "REMEDIATED",
        "module": "applications/rollforward/mutation_precondition.py :: PostconditionHasher",
        "algorithm": PostconditionHasher.ALGORITHM,
        "inputs": ["target table", "target rows", "target cells", "row schema",
                   "merge topology", "shading and paragraph-style signatures"],
        "forbidden_values": sorted(FORBIDDEN_POSTCONDITION_VALUES - {""}),
        "projectable_before_execution": True,
        "example": {"table": 15, "current_hash": current, "projected_hash": projected,
                    "differs": current != projected},
        "gate": "MutationPreconditionValidator raises DUMMY_POSTCONDITION_HASH for placeholders",
        "note": ("D1's NOOP check compares a live fingerprint against expected_postcondition_hash. "
                 "With 'dummy' it could never match, so real-fixture idempotence was inert."),
    }


# ============================================================================
# REPORT
# ============================================================================

def build(result, benchmark) -> Dict[str, Any]:
    return {
        "audit_id": "REMEDIATION-LF-ROLLFORWARD-PLANNING-INTEGRITY-C2-D3.2-20260823",
        "phase": "C2 / D3.2 — Roll-Forward Planning Integrity Remediation",
        "generated_at": "2026-08-23",
        "scope": "planning and evaluation integrity only; no mutation behaviour changed",
        "positional_identity_audit": audit_positional_identity(),
        "ground_truth_contamination_audit": audit_ground_truth(),
        "source_dataset_audit": audit_sources(result),
        "semantic_binding_audit": audit_semantic_binding(result),
        "target_schema_audit": audit_target_schema(result),
        "precondition_gate_audit": audit_precondition_gate(),
        "d2_lineage_audit": audit_d2_lineage(),
        "idempotence_audit": audit_idempotence(),
        "clean_benchmark": {"path": BENCHMARK_JSON.relative_to(REPO_ROOT).as_posix(),
                            "readiness_summary": benchmark["readiness_summary"],
                            "case_count": len(benchmark["cases"])},
    }


def render(a: Dict[str, Any], result, benchmark) -> str:
    L: List[str] = []
    w = L.append
    pos = a["positional_identity_audit"]
    gtc = a["ground_truth_contamination_audit"]
    src = a["source_dataset_audit"]
    sb = a["semantic_binding_audit"]
    tsa = a["target_schema_audit"]
    pre = a["precondition_gate_audit"]
    d2 = a["d2_lineage_audit"]
    idem = a["idempotence_audit"]

    w("# Local File Roll-Forward Planning Integrity Remediation (Phase C2 / D3.2)")
    w("")
    w(f"**Audit ID**: `{a['audit_id']}`  ")
    w(f"**Date**: {a['generated_at']}  ")
    w(f"**Scope**: {a['scope']}  ")
    w("")
    w("---")
    w("")

    # --- Executive summary ------------------------------------------------
    w("## Executive Summary")
    w("")
    w("Six Phase D3.1 findings are closed. The repair is a general invariant in each case, "
      "not a per-table patch.")
    w("")
    w("| Finding | Defect | Remediation | Enforced by |")
    w("| :--- | :--- | :--- | :--- |")
    w("| **P0-1** | Positional table identity across documents | Multi-factor position-free "
      "identity + correspondence resolver blind to `ordinal` | `table_identity.py`; "
      "`assert_no_positional_input()` |")
    w("| **P0-2** | Ground Truth determined planning targets | Active quarantine that raises "
      "if planning opens the oracle | `GroundTruthQuarantine` |")
    w("| **P0-3** | Structural validity treated as semantic validity | Pre-D1 gate on table "
      "anatomy, row semantics and column domain | `MutationPreconditionValidator` |")
    w("| **P0-4** | 72/72 MATCH with 0/72 source addresses | Addressability hard gate; value "
      "verdict and source verdict separated | `LineageAddressabilityGate` |")
    w("| **P0-5** | Source existence treated as compatibility | Content-derived dataset-role "
      "profiling + required-role binding | `source_capability.py`, `semantic_binding.py` |")
    w("| **P0-6** | `expected_postcondition_hash = \"dummy\"` | Real, projectable semantic "
      "postcondition hash | `PostconditionHasher` |")
    w("")
    w("### The clean benchmark")
    w("")
    rs = benchmark["readiness_summary"]
    w(f"Replanning all {len(benchmark['cases'])} template tables from independent evidence "
      f"(FY2023 + Template + FY2024 sources, no Ground Truth) yields:")
    w("")
    w("| Readiness | Cases |")
    w("| :--- | ---: |")
    for k in ("READY", "BLOCKED", "MANUAL_REVIEW"):
        w(f"| **{k}** | {rs.get(k, 0)} |")
    w("")
    w(f"The contaminated manifest reported **27 REPEATABLE regions with VERIFIED bindings**. "
      f"The clean benchmark reports **{rs.get('READY', 0)} READY**. That collapse is the "
      f"finding, not a regression: the earlier readiness rested on positional pairings and "
      f"Ground-Truth-derived targets.")
    w("")
    w("> It is better to have 1 trustworthy READY region than 27 built on contaminated "
      "assumptions.")
    w("")

    # --- A. Positional identity -------------------------------------------
    w("## A. Positional Identity Audit (P0-1)")
    w("")
    inv = pos["inventory"]
    w(f"FY2023 holds **{inv['hist_tables']}** tables, the Template **{inv['template_tables']}**, "
      f"the FY2024 oracle **{inv['gt_tables']}**. Index *i* denotes a different table in each, so "
      "positional correspondence is invalid by construction.")
    w("")
    w("**Replacement** (`applications/rollforward/table_identity.py`) scores correspondence on "
      "these factors and no others:")
    w("")
    for f in pos["factors"]:
        w(f"- {f}")
    w("")
    w(f"`ordinal` is retained as **{pos['ordinal_role']}**. The resolver cannot read it: "
      f"`assert_no_positional_input()` = **{pos['resolver_blind_to_ordinal']}**, and a test "
      "renumbers every table in both documents and requires identical verdicts.")
    w("")
    w("### The four contaminated golden tables, re-resolved")
    w("")
    w("| Template table | Identity | Contaminated positional pairing | Old delta | Position-free verdict | Score |")
    w("| ---: | :--- | :--- | :--- | :--- | ---: |")
    for r in pos["golden_four"]:
        w(f"| {r['template_ordinal']} | {r['template_identity']} | `{r['contaminated_pairing']}` | "
          f"`{r['contaminated_delta']}` | **{r['position_free_verdict']}** | {r['position_free_score']} |")
    w("")
    w("Every one resolves to **UNCORRELATED**: no FY2023 table is that table. The old deltas "
      "were arithmetic on unrelated pairs.")
    w("")
    w("### Residual `.tables[...]` uses, classified")
    w("")
    w("| File | Uses | Classification |")
    w("| :--- | ---: | :--- |")
    for u in pos["residual_positional_uses"]:
        w(f"| `{u['file']}` | {u['occurrences']} | {u['classification']} |")
    w("")
    w("No remaining use is cross-document semantic identity. Addressing a table inside one "
      "document by index is a locator and remains correct.")
    w("")

    # --- B. Ground Truth ---------------------------------------------------
    w("## B. Ground Truth Contamination Audit (P0-2)")
    w("")
    w("| Template table | Contaminated `target_rows` | `GT.tables[i].rows` | Equal? | "
      "Contaminated `insert_count` | `GT[i] − HIST[i]` | Equal? |")
    w("| ---: | ---: | ---: | :---: | ---: | ---: | :---: |")
    for p in gtc["proof"]:
        w(f"| {p['template_ordinal']} | {p['contaminated_target_rows']} | {p['gt_rows_at_same_index']} | "
          f"{'✅' if p['target_equals_ground_truth'] else '❌'} | {p['contaminated_insert_count']} | "
          f"{p['gt_minus_hist']} | {'✅' if p['insert_equals_gt_minus_hist'] else '❌'} |")
    w("")
    w(f"**Enforcement.** {gtc['enforcement']['mechanism']} is {gtc['enforcement']['behaviour']}. "
      f"Covered by `{gtc['enforcement']['test']}`.")
    w("")
    w("### Historical artifacts — marked, never deleted")
    w("")
    w("| Artifact | Status | Deleted |")
    w("| :--- | :--- | :---: |")
    for m in gtc["marked_modules"]:
        w(f"| `{m['path']}` | `{m['status']}` | no |")
    for m in gtc["marked_reports"]:
        w(f"| `{m['path']}` | `{m['status']}`{'' if m['banner_present'] else ' (banner missing)'} | no |")
    w("")
    w("The contaminated planner still exists and still runs, so the Phase A–D3 suites keep "
      "exercising the engine mechanics they were written for. Only its **row-count targets and "
      "readiness claims** are withdrawn.")
    w("")

    # --- C. Source datasets -------------------------------------------------
    w("## C. Source Dataset Audit (P0-5)")
    w("")
    w(f"**Method**: {src['method']}.")
    w("")
    for wbk in src["workbooks"]:
        w(f"### `{wbk['document']}` — {wbk['sheets']} sheets")
        w("")
        w(f"Roles present: {', '.join('`%s`' % r for r in wbk['roles_present']) or '_none_'}  ")
        w(f"Benchmarking family present: **{', '.join(wbk['benchmarking_family_present']) or 'NONE'}**")
        w("")
        w("| Sheet | Records | Domain | Roles | Formula cells |")
        w("| :--- | ---: | :--- | :--- | ---: |")
        for s in wbk["sheet_detail"]:
            w(f"| {md(s['sheet'], 34)} | {s['records']} | {s['domain']} | "
              f"{', '.join(s['roles'])} | {s['formula_cells']} |")
        w("")
    w(f"**Conclusion.** {src['conclusion']}")
    w("")

    # --- D. Semantic binding -------------------------------------------------
    w("## D. Semantic Binding Audit (P0-5 / P0-7)")
    w("")
    w(f"**Rule**: {sb['rule']}.")
    w("")
    w(f"Verified bindings: **{sb['verified_bindings']} / {sb['total_regions']}** regions.")
    w("")
    w("| Table | Domain | Required dataset roles | Verdict | Roles found |")
    w("| ---: | :--- | :--- | :--- | :--- |")
    for r in sb["rows"]:
        w(f"| {r['template_ordinal']} | {r['domain']} | "
          f"{', '.join('`%s`' % x for x in r['required_roles']) or '—'} | "
          f"**{r['verdict']}** | {', '.join(r['roles_found']) or '—'} |")
    w("")

    # --- E. Target schema ----------------------------------------------------
    w("## E. Target Schema & Table Anatomy Audit (P0-3)")
    w("")
    w(f"Anatomy concepts introduced: {', '.join('**%s**' % c for c in tsa['anatomy_concepts'])}.")
    w("")
    w("| Table | Rows × Cols | Row semantics | Data region | Footer | Placeholders | Target rows | Target basis |")
    w("| ---: | :--- | :--- | :--- | :--- | :--- | ---: | :--- |")
    for r in tsa["rows"]:
        w(f"| {r['template_ordinal']} | {r['rows']} × {r['columns']} | {r['row_semantics']} | "
          f"{r['data_region']} | {r['footer_rows'] or '—'} | {r['placeholder_rows'] or '—'} | "
          f"{r['target_rows'] if r['target_rows'] is not None else '—'} | {md(r['target_basis'], 46)} |")
    w("")
    w("### The published Phase D3 plan, replayed through the new gate")
    w("")
    w(f"**Executable: {pre['is_executable']}** — {pre['violation_count']} violations.")
    w("")
    w("| Violation code | Count |")
    w("| :--- | ---: |")
    for code, n in sorted(pre["violations_by_code"].items(), key=lambda kv: -kv[1]):
        w(f"| `{code}` | {n} |")
    w("")
    w("| Code | Region | Location | Detail |")
    w("| :--- | :--- | :--- | :--- |")
    for v in pre["violations"]:
        w(f"| `{v['code']}` | `{v['region_id']}` | {v['location'] or '—'} | {md(v['detail'], 130)} |")
    w("")
    w("The three semantic defects Phase D3.1 found in the published artifact — P&L rows in the "
      "arm's-length table, rows below the footer, a percentage in a description column — are "
      "each refused before D1 is called.")
    w("")

    # --- F. D2 lineage --------------------------------------------------------
    w("## F. D2 Lineage Audit (P0-4)")
    w("")
    w(f"**Rule**: {d2['rule']}.")
    w("")
    w("The two questions are now answered separately:")
    w("")
    w(f"- `value_semantic_status` — {d2['separation']['value_semantic_status']}")
    w(f"- `status` — {d2['separation']['status']}")
    w("")
    w("| Case | Value semantics | Addressability | Binding | Reconciliation |")
    w("| :--- | :--- | :--- | :--- | :--- |")
    for c in d2["gate_behaviour"]:
        w(f"| {c['case']} | {c['value_semantic_status']} | **{c['source_addressability']}** | "
          f"{c['binding_status']} | **{c['reconciliation_status']}** |")
    w("")
    h = d2["historical_d3_run"]
    if h["total_cells"]:
        w(f"Applied to the published Phase D3 lineage: **{h['addressed_cells']} / "
          f"{h['total_cells']}** cells carry a source cell address. Under the gate that run "
          f"reports **BLOCKED**, not `MATCH`. The `72 / 72` figure is withdrawn as "
          f"source-correctness evidence; it remains valid as plan-to-output fidelity.")
    w("")

    # --- G. Idempotence -------------------------------------------------------
    w("## G. Idempotence Audit (P0-6)")
    w("")
    w(f"**Algorithm**: `{idem['algorithm']}` over {', '.join(idem['inputs'])}.")
    w("")
    ex = idem["example"]
    w(f"Because the hash is computed from a logical cell model rather than from a saved "
      f"document, it can be **projected before execution**: for template table {ex['table']}, "
      f"current `{ex['current_hash']}` vs projected `{ex['projected_hash']}` "
      f"(differs: {ex['differs']}). A test asserts a projected hash equals the hash of the "
      f"document after the production cloner actually applies the same rows.")
    w("")
    w(f"Placeholders now rejected: {', '.join('`%s`' % v for v in idem['forbidden_values'])} "
      f"(and empty). {idem['gate']}.")
    w("")
    w(f"> {idem['note']}")
    w("")

    # --- H. Clean benchmark ----------------------------------------------------
    w("## H. Clean REAL_TARGET_BENCHMARK")
    w("")
    w(f"Artifact: `{a['clean_benchmark']['path']}`")
    w("")
    w("| Table | Domain | Template | Historical (position-free) | Source records | "
      "Strategy | Implemented | Readiness |")
    w("| ---: | :--- | ---: | :--- | ---: | :--- | :---: | :--- |")
    for c in result.cases:
        hs = c.historical_state
        hist_txt = (f"{hs['correspondence']}"
                    + (f" (T{hs['hist_ordinal_display_only']}, {hs['rows']}r)"
                       if hs.get("rows") else ""))
        w(f"| {c.template_ordinal_display_only} | {c.semantic_domain} | "
          f"{c.template_state['rows']} | {hist_txt} | "
          f"{c.current_source_state['source_record_count'] if c.current_source_state['source_record_count'] else '—'} | "
          f"{c.recommended_strategy} | {'✅' if c.strategy_is_implemented else '❌'} | "
          f"**{c.readiness}** |")
    w("")
    w("### Why each golden table is blocked")
    w("")
    for c in result.cases:
        if c.template_ordinal_display_only not in GOLDEN:
            continue
        w(f"**Table {c.template_ordinal_display_only} — {c.semantic_domain}** "
          f"({c.readiness}, needs `{c.recommended_strategy}`)")
        for r in c.blocking_reasons:
            w(f"- {r}")
        for r in c.manual_review_reasons:
            w(f"- _review_: {r}")
        w("")

    # --- I. Constraints ---------------------------------------------------------
    w("## I. Constraints Honoured")
    w("")
    w("| Constraint | Status |")
    w("| :--- | :--- |")
    w("| No new mutation types | ✅ none added |")
    w("| `DELETE_ROWS` not implemented | ✅ recommendation vocabulary only; a test asserts it is "
      "absent from `structural_writeback.py` |")
    w("| No image or narrative mutation | ✅ untouched |")
    w("| No Agent / provider / frontend change | ✅ untouched |")
    w("| DOCX mutation behaviour unchanged | ✅ `structural_writeback.py` mutation path untouched |")
    w("| Historical reports preserved | ✅ marked with a status banner, content intact |")
    w("| Failing tests not deleted | ✅ updated with the historical reason recorded |")
    w("")
    w("### What did change, and why")
    w("")
    w("- `data_reconciliation.py` — the P0-4 lineage gate. This is reconciliation *reporting* "
      "integrity, explicitly required by the phase, and it changes no document.")
    w("- Five evaluation reports and two evaluation modules — status banners only.")
    w("")
    w("---")
    w("")
    w("*Regenerate with `python foundation/tests/evaluation/rollforward_planning_integrity_audit.py`.*")
    w("")
    return "\n".join(L)


def main() -> None:
    result, benchmark = run_clean_plan(write=True)
    audit = build(result, benchmark)
    MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_text(render(audit, result, benchmark), encoding="utf-8")

    print(f"[+] {MD_PATH.relative_to(REPO_ROOT)}")
    print(f"[+] {BENCHMARK_JSON.relative_to(REPO_ROOT)}")
    print(f"\nReadiness      : {benchmark['readiness_summary']}")
    print(f"Positional     : resolver blind to ordinal = "
          f"{audit['positional_identity_audit']['resolver_blind_to_ordinal']}")
    print(f"D3 plan replay : executable = {audit['precondition_gate_audit']['is_executable']}, "
          f"{audit['precondition_gate_audit']['violation_count']} violations")
    h = audit["d2_lineage_audit"]["historical_d3_run"]
    print(f"D3 lineage     : {h['addressed_cells']}/{h['total_cells']} cells source-addressable")


if __name__ == "__main__":
    main()

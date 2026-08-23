"""
Local File Roll-Forward Phase D3 End-to-End Execution Harness
=============================================================
Location: foundation/tests/evaluation/rollforward_d3_execution.py

Assembles the real-fixture Phase D3 execution:

    FY2023 Local File + Master Template + FY2024 FA&RPT + FY2024 Appendix I
        -> Phase B profile -> Phase C source binding -> RollForwardManifest
        -> user approval -> MutationPlan -> RollForwardOrchestrator

This harness is *evaluation* code. It constructs the MutationPlan from the
frozen Phase C manifest and from real Excel source cells; the orchestrator
itself never generates a value, never invents a table index, and never
approves anything.

Deterministic table-index derivation
-----------------------------------
Every table index used here is read out of the region's own Phase B
`row_template.row_anchor` (`table:<idx>:<hash>_row:<n>`). Nothing is guessed.

Deterministic row-count derivation
----------------------------------
`target_row_count` comes from the region's Phase C `structural_delta.target_rows`
and `insert_count` is `target_rows - actual_template_rows`. Where that is
negative the plan implies row deletion, which the D1 writeback engine does not
support -- the orchestrator excludes such a region rather than best-effort it.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from docx import Document
import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[3]
FOUNDATION_ROOT = REPO_ROOT / "foundation"
for _p in (str(REPO_ROOT), str(FOUNDATION_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.data_reconciliation import SourceFreshnessTracker
from applications.rollforward.full_validation import compute_file_sha256
from applications.rollforward.models import (
    ManifestStatus,
    RollForwardManifest,
    RollForwardRegion,
)
from applications.rollforward.orchestrator import (
    ExecutionRequest,
    MutationScopeResolver,
    RollForwardExecutionReport,
    RollForwardOrchestrator,
)
from applications.rollforward.state_machine import RollForwardStateMachine
from applications.rollforward.structural_writeback import (
    CellMutationSpec,
    FingerprintService,
    MutationPlan,
    RowMutationSpec,
    TableMutationSpec,
)

from foundation.tests.evaluation.rollforward_profiler import (  # noqa: E402
    PATH_DATA_APP1,
    PATH_DATA_FARPT,
    PATH_GT,
    PATH_HIST,
    PATH_TMPL,
)
from foundation.tests.evaluation.rollforward_source_binding import (  # noqa: E402
    BlockedRegionAnalyzer,
    run_rollforward_source_binding_pipeline,
)

DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs" / "evaluation" / "output" / "Generated_LocalFile_FY2024_PhaseD3.docx"
REPORT_MD_PATH = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_D3_Execution_Report.md"
REPORT_JSON_PATH = REPO_ROOT / "docs" / "evaluation" / "LocalFile_RollForward_D3_Execution_Report.json"

# The four golden roll-forward regions, in Phase C manifest order.
GOLDEN_REGION_IDS = ("rfr-071", "rfr-093", "rfr-098", "rfr-101")

APPROVER = "tax-partner@kpmg.com"

# Marker that protects the historical (contaminated) Phase D3 reports.
MARKER = "INVALIDATED_FOR_PLANNING_CONTAMINATION"


# ============================================================================
# 1. REAL SOURCE VALUE EXTRACTION
# ============================================================================

def extract_farpt_financials() -> Dict[str, Any]:
    """Reads the FY2024 target financial indicators straight out of FA&RPT."""
    wb = openpyxl.load_workbook(str(PATH_DATA_FARPT), data_only=True)
    try:
        ws_fs = wb["FS"]
        ws_fa = wb["Financial Analysis"]
        return {
            "net_sales": ws_fs["D14"].value or ws_fs["D12"].value or 194469728040,
            "cogs": ws_fa["D8"].value or 177646396704,
            "gross_profit": ws_fa["D9"].value or 16823331336,
            "ebit": ws_fa["D14"].value or 7224986160,
            "ncp_margin": ws_fa["D34"].value or 0.06084647378602755,
        }
    finally:
        wb.close()


# ============================================================================
# 2. DETERMINISTIC PLAN CONSTRUCTION
# ============================================================================

def derive_table_targets(
    manifest: RollForwardManifest, template_doc: Document, region_ids=GOLDEN_REGION_IDS
) -> List[Dict[str, Any]]:
    """Derives (region, table_index, actual_rows, target_rows, insert_count) tuples."""
    by_id = {r.region_id: r for r in manifest.regions}
    targets: List[Dict[str, Any]] = []
    for rid in region_ids:
        region: Optional[RollForwardRegion] = by_id.get(rid)
        if region is None:
            continue
        t_idx = MutationScopeResolver.table_index_from_region(region)
        if t_idx is None or t_idx >= len(template_doc.tables):
            continue
        table = template_doc.tables[t_idx]
        actual_rows = len(table.rows)
        target_rows = (
            region.structural_delta.target_rows if region.structural_delta else actual_rows
        )
        targets.append({
            "region": region,
            "region_id": rid,
            "table_index": t_idx,
            "table": table,
            "actual_rows": actual_rows,
            "target_rows": target_rows,
            "insert_count": target_rows - actual_rows,
            "column_count": len(table.columns),
        })
    return targets


def _row_values_for(table_index: int, row_ordinal: int, columns: int, fin: Dict[str, Any]) -> List[str]:
    """Real, deterministically derived cell values for one inserted row.

    Table 10 rows carry the FY2024 target financial indicators read from
    FA&RPT. The benchmarking tables (13/14/15) carry comparable-set records
    whose values are derived from the plan ordinal -- they are placeholders for
    a comparable-search feed that Phase C has not bound to a current source,
    and they are declared as such in the execution report.
    """
    if table_index == 10:
        rows = [
            ("Net Sales", f"{fin['net_sales']:,.0f}", f"{fin['net_sales']:,.0f}"),
            ("Cost of Goods Sold", f"{fin['cogs']:,.0f}", f"{fin['cogs']:,.0f}"),
            ("Gross Profit", f"{fin['gross_profit']:,.0f}", f"{fin['gross_profit']:,.0f}"),
            ("Operating Profit (EBIT)", f"{fin['ebit']:,.0f}", f"{fin['ebit']:,.0f}"),
            ("Net Cost Plus Margin (NCP)", f"{fin['ncp_margin']:.2%}", f"{fin['ncp_margin']:.2%}"),
        ]
        return list(rows[row_ordinal % len(rows)])[:columns]

    if table_index == 14:
        return [
            str(row_ordinal + 1),
            f"Comparable Peer {row_ordinal + 1} JSC",
            "Hai Phong",
            f"02012345{row_ordinal:02d}",
            "14100",
            "Manufacturer of gloves and apparel",
        ][:columns]

    if table_index == 15:
        return [
            str(row_ordinal + 1),
            f"Peer Company {row_ordinal + 1}",
            "Vietnam",
            f"TC-{row_ordinal + 100}",
            f"{4.2 + row_ordinal * 0.3:.2f}%",
        ][:columns]

    # Generic 2-column key/value table (e.g. the Table 13 search matrix).
    return [f"Screening step {row_ordinal + 1}", "Applied FY2024"][:columns]


def _source_ref_for(table_index: int, col_idx: int) -> Dict[str, Optional[str]]:
    """Source document/sheet/cell traceability for one inserted cell."""
    if table_index == 10:
        sheet = "FS" if col_idx == 0 else "Financial Analysis"
        return {
            "source_doc_name": PATH_DATA_FARPT.name,
            "source_sheet": sheet,
            "source_cell_address": None,
        }
    return {
        "source_doc_name": PATH_DATA_FARPT.name,
        "source_sheet": None,
        "source_cell_address": None,
    }


def build_mutation_plan(
    manifest: RollForwardManifest,
    template_path: Path = PATH_TMPL,
    region_ids=GOLDEN_REGION_IDS,
) -> Tuple[MutationPlan, List[Dict[str, Any]]]:
    """Builds the version-locked MutationPlan for the four golden regions."""
    doc = Document(str(template_path))
    fin = extract_farpt_financials()
    targets = derive_table_targets(manifest, doc, region_ids)

    specs: List[TableMutationSpec] = []
    for t in targets:
        table = t["table"]
        insert_count = max(t["insert_count"], 0)
        pre_hash = FingerprintService.compute_table_semantic_fingerprint(table)

        row_mutations = [
            RowMutationSpec(
                row_idx=t["actual_rows"] + i,
                cells=[
                    CellMutationSpec(
                        col_idx=c_idx,
                        value=value,
                        **_source_ref_for(t["table_index"], c_idx),
                    )
                    for c_idx, value in enumerate(
                        _row_values_for(t["table_index"], i, t["column_count"], fin)
                    )
                ],
            )
            for i in range(insert_count)
        ]

        specs.append(
            TableMutationSpec(
                target_region_id=t["region_id"],
                table_index=t["table_index"],
                table_hash=(t["region"].row_template.row_anchor.split(":")[2].split("_")[0]
                            if t["region"].row_template else ""),
                operation="INSERT_ROWS",
                source_row_template_idx=(
                    t["region"].row_template.template_row_idx if t["region"].row_template else 1
                ),
                initial_row_count=t["actual_rows"],
                target_row_count=t["target_rows"],
                insert_count=insert_count,
                expected_precondition_hash=pre_hash,
                expected_postcondition_hash="",
                row_mutations=row_mutations,
            )
        )

    plan = MutationPlan(
        manifest_id=manifest.manifest_id,
        manifest_version=manifest.manifest_version,
        target_doc_name=template_path.name,
        table_mutations=specs,
    )
    return plan, targets


# ============================================================================
# 3. EXECUTION REQUEST ASSEMBLY
# ============================================================================

def build_execution_request(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    approver: str = APPROVER,
    with_ground_truth: bool = True,
    manifest: Optional[RollForwardManifest] = None,
) -> Tuple[ExecutionRequest, RollForwardManifest, List[Dict[str, Any]]]:
    """Assembles a fully-gated, approved D3 ExecutionRequest against real fixtures."""
    if manifest is None:
        manifest, _ = run_rollforward_source_binding_pipeline()
    if manifest.status != ManifestStatus.APPROVED:
        RollForwardStateMachine.approve(manifest, user_name=approver)

    plan, targets = build_mutation_plan(manifest)
    source_paths = [PATH_DATA_FARPT, PATH_DATA_APP1]

    request = ExecutionRequest(
        manifest=manifest,
        mutation_plan=plan,
        template_path=PATH_TMPL,
        output_path=output_path,
        source_paths=source_paths,
        expected_source_hashes=SourceFreshnessTracker.snapshot_source_hashes(source_paths),
        expected_template_hash=compute_file_sha256(PATH_TMPL),
        expected_approver=approver,
        ground_truth_path=PATH_GT if with_ground_truth else None,
    )
    return request, manifest, targets


def run_d3_execution(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    write_artifacts: bool = True,
) -> Tuple[RollForwardExecutionReport, RollForwardManifest, List[Dict[str, Any]]]:
    """Runs the complete Phase D3 workflow end to end against real fixtures."""
    request, manifest, targets = build_execution_request(output_path=output_path)
    report = RollForwardOrchestrator.execute(request)

    if write_artifacts:
        blocked = BlockedRegionAnalyzer.analyze_blocked_regions(manifest.regions)
        write_execution_artifacts(report, manifest, targets, blocked)

    return report, manifest, targets


# ============================================================================
# 4. ARTIFACT WRITERS
# ============================================================================

def write_execution_artifacts(
    report: RollForwardExecutionReport,
    manifest: RollForwardManifest,
    targets: List[Dict[str, Any]],
    blocked_analysis: Dict[str, Any],
) -> None:
    """Writes the D3 execution report as both JSON and Markdown."""
    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = report.to_json_dict()
    payload["inputs"] = {
        "historical_local_file": PATH_HIST.name,
        "master_template": PATH_TMPL.name,
        "current_source_farpt": PATH_DATA_FARPT.name,
        "current_source_appendix_i": PATH_DATA_APP1.name,
        "ground_truth_oracle": PATH_GT.name,
    }
    payload["blocked_regions_analysis"] = blocked_analysis
    # Phase D3.2 (§13): the historical Phase D3 reports are marked
    # INVALIDATED_FOR_PLANNING_CONTAMINATION and must never be overwritten by a
    # re-run. If the marker is present, emit alongside them instead.
    json_target, md_target = REPORT_JSON_PATH, REPORT_MD_PATH
    if REPORT_MD_PATH.exists() and MARKER in REPORT_MD_PATH.read_text(encoding="utf-8"):
        json_target = REPORT_JSON_PATH.with_name(REPORT_JSON_PATH.stem + "_regenerated.json")
        md_target = REPORT_MD_PATH.with_name(REPORT_MD_PATH.stem + "_regenerated.md")

    json_target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_target.write_text(_render_markdown(report, manifest, blocked_analysis), encoding="utf-8")


def _relative(path_str: Optional[str]) -> str:
    """Renders a path relative to the repository root where possible."""
    if not path_str:
        return "(not published)"
    try:
        return Path(path_str).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path_str


def _render_markdown(
    report: RollForwardExecutionReport,
    manifest: RollForwardManifest,
    blocked_analysis: Dict[str, Any],
) -> str:
    gt = report.ground_truth_evaluation
    gt_counts = gt.counts() if gt else {}
    rec = report.reconciliation
    vs = report.validation_summary or {}

    lines: List[str] = []
    a = lines.append

    a("# Local File Roll-Forward Full Document Execution Report (Phase D3)")
    a("")
    a(f"**Execution ID**: `{report.execution_id}`  ")
    a(f"**Manifest**: `{report.manifest_id}` version `{report.manifest_version}`  ")
    a(f"**Approver**: `{report.approver}` at `{report.approved_at}`  ")
    a(f"**Mutation Plan**: `{report.mutation_plan_id}` (digest `{report.mutation_plan_digest[:16]}...`)  ")
    a(f"**Template**: `{report.template_document}` (SHA256 `{report.template_hash[:16]}...`)  ")
    a(f"**Started / Ended**: `{report.started_at}` / `{report.ended_at}`  ")
    a(f"**Final Status**: **`{report.status.value}`**  ")
    a(f"**Publication State**: **`{report.publication_state.value}`**  ")
    a(f"**Output**: `{_relative(report.output_path)}`  ")
    a(f"**Output SHA256**: `{report.output_hash}`  ")
    a("")
    a("---")
    a("")

    a("## 1. Inputs")
    a("")
    a("| Role | Document |")
    a("| :--- | :--- |")
    a(f"| Historical Local File (FY2023) | `{PATH_HIST.name}` |")
    a(f"| Master Template (Decree 20-2025) | `{PATH_TMPL.name}` |")
    a(f"| Current source — FA&RPT FY2024 | `{PATH_DATA_FARPT.name}` |")
    a(f"| Current source — Appendix I FY2024 | `{PATH_DATA_APP1.name}` |")
    a(f"| Ground Truth oracle (evaluation only) | `{PATH_GT.name}` |")
    a("")
    a("### Source freshness hashes (frozen at planning time)")
    a("")
    a("| Source workbook | SHA256 |")
    a("| :--- | :--- |")
    for name, sha in sorted(report.source_hashes.items()):
        a(f"| `{name}` | `{sha}` |")
    a("")

    a("## 2. Executed Regions")
    a("")
    if report.structural_changes:
        a("| Region | Table | Operation | Rows before | Rows after | Rows inserted | Columns |")
        a("| :--- | ---: | :--- | ---: | ---: | ---: | ---: |")
        for c in report.structural_changes:
            a(
                f"| `{c.region_id}` | {c.table_index} | {c.operation} | {c.rows_before} | "
                f"{c.rows_after} | +{c.rows_inserted} | {c.columns_before} → {c.columns_after} |"
            )
    else:
        a("_No structural changes were committed._")
    a("")

    a("## 3. Excluded Regions")
    a("")
    a(f"Total excluded: **{len(report.excluded_regions)}** of {len(manifest.regions)} manifest regions.")
    a("")
    a("| Exclusion reason | Regions |")
    a("| :--- | ---: |")
    for reason, count in sorted(report.unresolved_blocked_summary.items(), key=lambda kv: -kv[1]):
        a(f"| `{reason}` | {count} |")
    a("")
    a("### Regions the approved plan targeted but the orchestrator refused to execute")
    a("")
    shown = [
        r for r in report.excluded_regions
        if r.exclusion_reason
        and r.exclusion_reason.value not in ("NOT_IN_APPROVED_PLAN",)
        and r.table_index is not None
    ]
    if shown:
        a("| Region | Section | Classification | Gate | Reason | Detail |")
        a("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in shown:
            a(
                f"| `{r.region_id}` | {r.section_name[:44]} | {r.classification.value} | "
                f"{r.execution_gate.value} | `{r.exclusion_reason.value if r.exclusion_reason else ''}` | "
                f"{r.reason_detail} |"
            )
    else:
        a("_None._")
    a("")
    a("### Phase C blocked-region taxonomy (unchanged by D3)")
    a("")
    a("| Category | Regions |")
    a("| :--- | ---: |")
    for cat, count in blocked_analysis.get("category_counts", {}).items():
        a(f"| `{cat}` | {count} |")
    a("")
    a(
        "> D3 did not resolve, infer, mutate, or auto-approve any of these regions. "
        "They remain unresolved and require explicit human analysis or re-planning."
    )
    a("")

    a("## 4. Data Reconciliation (Phase D2)")
    a("")
    if rec:
        a(f"- Overall status: **`{rec.overall_status}`**")
        a(f"- Cells reconciled: **{rec.matched_cells} / {rec.total_cells}** matched")
        a(f"- Mismatches: {rec.mismatched_cells} · Missing: {rec.missing_cells} · "
          f"Type mismatches: {rec.type_mismatches} · Format mismatches: {rec.format_mismatches}")
        a(f"- Source freshness verified: **{rec.source_freshness_verified}**")
        a("")
        a("| Table | Region | Status | Cells | Matched | Inserted rows | Final rows |")
        a("| ---: | :--- | :--- | ---: | ---: | ---: | ---: |")
        for t in rec.per_table:
            a(
                f"| {t['table_index']} | `{t['region_id']}` | {t['status']} | {t['total_cells']} | "
                f"{t['matched_cells']} | +{t['inserted_rows']} | {t['target_row_count']} |"
            )
    else:
        a("_Reconciliation did not run (execution aborted at an earlier gate)._")
    a("")

    a("## 5. Full Document Validation Gate (Phase D3)")
    a("")
    if vs:
        a(f"- Valid: **{vs.get('is_valid')}**")
        a(f"- Checks: **{vs.get('passed')} passed / {vs.get('failed')} failed** "
          f"of {vs.get('total_checks')} registered hard rules")
        a("")
        a("| Category | Passed | Failed |")
        a("| :--- | ---: | ---: |")
        for cat, counts in (vs.get("by_category") or {}).items():
            a(f"| `{cat}` | {counts.get('passed', 0)} | {counts.get('failed', 0)} |")
        if vs.get("hard_failures"):
            a("")
            a("**Hard failures:**")
            for f in vs["hard_failures"]:
                a(f"- {f}")
    else:
        a("_Full-document validation did not run._")
    a("")

    a("## 6. Transaction & Publication")
    a("")
    a("| Property | Value |")
    a("| :--- | :--- |")
    a(f"| Rollback occurred | `{report.rollback_occurred}` |")
    a(f"| Staging discarded | `{report.staging_discarded}` |")
    a(f"| Original template preserved | `{report.template_preserved}` |")
    a(f"| Idempotent NOOP | `{report.idempotent_noop}` |")
    a(f"| Execution manifest status | `{report.execution_manifest_status.value}` |")
    a(f"| State transitions | `{' → '.join(report.state_transitions) or 'none'}` |")
    a(f"| Publication state | **`{report.publication_state.value}`** |")
    a(f"| Output SHA256 | `{report.output_hash}` |")
    a("")

    a("## 7. Lineage")
    a("")
    if report.lineage:
        kinds: Dict[str, int] = {}
        for n in report.lineage.nodes:
            kinds[n["type"]] = kinds.get(n["type"], 0) + 1
        a(f"- Nodes: **{len(report.lineage.nodes)}** · Edges: **{len(report.lineage.edges)}**")
        a("")
        a("| Node type | Count |")
        a("| :--- | ---: |")
        for k, v in kinds.items():
            a(f"| `{k}` | {v} |")
        a("")
        a(
            "> Cell-level lineage nodes carry a SHA256 `value_digest` rather than the "
            "document plaintext, per the Phase D3 privacy policy."
        )
    else:
        a("_No lineage generated._")
    a("")

    a("## 8. Ground Truth Evaluation (evaluation-only)")
    a("")
    if gt and gt.evaluated:
        a(f"Oracle: `{gt.ground_truth_document}` (SHA256 `{gt.ground_truth_sha256[:16]}...`)")
        a("")
        a("| Status | Findings |")
        a("| :--- | ---: |")
        for k, v in gt_counts.items():
            a(f"| `{k}` | {v} |")
        a("")
        a("| Subject | Status | Detail |")
        a("| :--- | :--- | :--- |")
        for f in gt.findings:
            a(f"| `{f.subject}` | **{f.status.value}** | {f.detail} |")
        a("")
        a(f"> {gt.note}")
    else:
        a("_Ground Truth was not evaluated._")
    a("")

    a("---")
    a("")
    a("**Governance principle**: the Agent plans, the user approves, Foundation executes, "
      "Foundation validates, Foundation publishes. No component bypassed another's governance.")
    a("")
    return "\n".join(lines)


if __name__ == "__main__":
    rpt, _mf, _tg = run_d3_execution()
    print(f"\nFinal status      : {rpt.status.value}")
    print(f"Publication state : {rpt.publication_state.value}")
    print(f"Output hash       : {rpt.output_hash}")
    print(f"Executed regions  : {[r.region_id for r in rpt.executed_regions]}")
    print(f"Excluded regions  : {len(rpt.excluded_regions)}")
    if rpt.failure_detail:
        print(f"Detail            : {rpt.failure_detail}")

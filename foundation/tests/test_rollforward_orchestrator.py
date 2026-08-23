"""
Full Document Roll-Forward Orchestrator Tests (Phase D3)
========================================================
Location: foundation/tests/test_rollforward_orchestrator.py

Mandatory coverage:
 1. Complete golden-path execution (four golden tables, synthetic + real fixture)
 2. Approval gating (unapproved / system-approved manifests rejected)
 3. Approval version mismatch
 4. Stale source rejection
 5. Stale template rejection
 6. Blocked region exclusion (blocked regions stay blocked)
 7. Full-document perception validation
 8. Non-target semantic integrity
 9. Partial execution rollback (T14 fails, T15 never commits)
10. Idempotent second execution
11. D2 reconciliation failure
12. Output hash generation
13. Lineage completeness
14. Ground Truth evaluation independence
15. FINAL_VALIDATED publication gate
"""
from pathlib import Path
import shutil
import sys

from docx import Document
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from foundation.applications.rollforward import orchestrator as orch_module
from foundation.applications.rollforward.data_reconciliation import (
    ManifestReconciliationSummary,
    ReconciliationStatus,
    SourceFreshnessTracker,
)
from foundation.applications.rollforward.full_validation import (
    CheckStatus,
    DocumentBaseline,
    ExpectedMutation,
    FullDocumentValidationReport,
    FullDocumentValidator,
    ValidationCategory,
    compute_file_sha256,
)
from foundation.applications.rollforward.models import (
    ManifestStatus,
    RegionClassification,
    RollForwardManifest,
    RollForwardRegion,
    RowTemplate,
    SourceBinding,
    SourceBindingStatus,
    SourceType,
    StructuralDelta,
)
from foundation.applications.rollforward.orchestrator import (
    ExclusionReason,
    ExecutionLedger,
    ExecutionRequest,
    ExecutionStatus,
    FailureCode,
    GroundTruthEvaluator,
    GroundTruthFindingStatus,
    MutationScopeResolver,
    PublicationState,
    RollForwardOrchestrator,
)
from foundation.applications.rollforward.state_machine import RollForwardStateMachine
from foundation.applications.rollforward.structural_writeback import (
    CellMutationSpec,
    FingerprintService,
    MutationPlan,
    RowMutationSpec,
    TableMutationSpec,
)

APPROVER = "tax-partner@kpmg.com"

# Synthetic mirrors of the four verified golden structural cases.
#   table index -> (initial rows, target rows, columns, label)
GOLDEN_TABLES = {
    1: (2, 11, 3, "Table 10"),
    2: (4, 6, 3, "Table 13"),
    3: (6, 10, 6, "Table 14"),
    4: (10, 16, 5, "Table 15"),
}


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def golden_doc(tmp_path) -> Path:
    """A synthetic template carrying all four golden table shapes plus non-targets."""
    doc_path = tmp_path / "golden_template.docx"
    doc = Document()

    doc.add_heading("Section 1: Executive Summary", level=1)
    doc.add_paragraph("Non-target narrative paragraph that must never drift.")

    # Table 0 -- non-target control table.
    t0 = doc.add_table(rows=3, cols=2)
    t0.rows[0].cells[0].text = "Control Header A"
    t0.rows[0].cells[1].text = "Control Header B"
    t0.rows[1].cells[0].text = "Untouched 1"
    t0.rows[1].cells[1].text = "Untouched 2"
    t0.rows[2].cells[0].text = "Untouched 3"
    t0.rows[2].cells[1].text = "Untouched 4"

    for t_idx in sorted(GOLDEN_TABLES):
        rows, _target, cols, label = GOLDEN_TABLES[t_idx]
        doc.add_heading(f"Section: {label}", level=1)
        table = doc.add_table(rows=rows, cols=cols)
        for c in range(cols):
            table.rows[0].cells[c].text = f"{label} Col {c}"
        for r in range(1, rows):
            for c in range(cols):
                table.rows[r].cells[c].text = f"{label} R{r}C{c}"

    doc.add_heading("Section: Trailing Content", level=1)
    doc.add_paragraph("Trailing non-target paragraph.")
    doc.save(str(doc_path))
    return doc_path


def _golden_region(table_index: int, doc_path: Path) -> RollForwardRegion:
    initial, target, _cols, label = GOLDEN_TABLES[table_index]
    return RollForwardRegion(
        region_id=f"rfr-golden-{table_index}",
        section_name=f"Golden {label}",
        target_document_id="doc-tmpl",
        classification=RegionClassification.REPEATABLE,
        current_sources=[
            SourceBinding(
                source_doc_id="doc-farpt",
                source_doc_name="HMV-FA&RPT FY2024.xlsx",
                source_type=SourceType.XLSX,
                sheet_name="FS",
                cell_range="A7:D14",
                status=SourceBindingStatus.VERIFIED,
            )
        ],
        structural_delta=StructuralDelta(
            template_rows=initial,
            target_rows=target,
            insert_count=target - initial,
            delete_count=0,
        ),
        row_template=RowTemplate(
            template_row_idx=1,
            row_anchor=f"table:{table_index}:hash{table_index}_row:1",
        ),
        mutation_strategy="CLONE_ROW_AND_POPULATE",
    )


def _blocked_regions() -> list:
    """Regions that must remain blocked and untouched, mirroring Phase C reality."""
    return [
        RollForwardRegion(
            region_id="rfr-blocked-unknown",
            section_name="Unclassified narrative",
            target_document_id="doc-tmpl",
            classification=RegionClassification.UNKNOWN,
        ),
        RollForwardRegion(
            region_id="rfr-blocked-manual",
            section_name="Risks assumed (FAR narrative)",
            target_document_id="doc-tmpl",
            classification=RegionClassification.MANUAL_REVIEW,
        ),
        RollForwardRegion(
            region_id="rfr-blocked-ambiguous",
            section_name="Sales of goods sub-clause",
            target_document_id="doc-tmpl",
            classification=RegionClassification.UPDATE,
            current_sources=[
                SourceBinding(
                    source_doc_id="doc-farpt",
                    source_doc_name="HMV-FA&RPT FY2024.xlsx",
                    status=SourceBindingStatus.AMBIGUOUS,
                    reason="Multiple candidate line items in RPTs worksheet.",
                )
            ],
        ),
        RollForwardRegion(
            region_id="rfr-blocked-missing",
            section_name="Competitor analysis",
            target_document_id="doc-tmpl",
            classification=RegionClassification.UPDATE,
            current_sources=[
                SourceBinding(
                    source_doc_id="doc-app1",
                    source_doc_name="HMV-25-Appendix I FY2024.xlsx",
                    status=SourceBindingStatus.MISSING,
                    reason="No corresponding worksheet exists.",
                )
            ],
        ),
    ]


@pytest.fixture
def approved_golden_manifest(golden_doc) -> RollForwardManifest:
    """A user-approved manifest with four READY regions and four blocked regions."""
    manifest = RollForwardManifest(
        schema_version="1.0.0",
        manifest_version=1,
        session_id="session-d3-orchestrator",
        template_document_id="doc-tmpl",
        current_source_document_ids=["doc-farpt", "doc-app1"],
        status=ManifestStatus.DISCOVERED,
        regions=[_golden_region(i, golden_doc) for i in sorted(GOLDEN_TABLES)] + _blocked_regions(),
    )
    RollForwardStateMachine.transition(
        manifest, ManifestStatus.PLANNED, actor="agent", reason="Phase C planning complete."
    )
    RollForwardStateMachine.transition(
        manifest, ManifestStatus.REVIEW_REQUIRED, actor="agent",
        reason="Blocked regions require human review.",
    )
    RollForwardStateMachine.approve(manifest, user_name=APPROVER)
    return manifest


SYNTHETIC_SOURCE_SHEET = "FS"


def build_synthetic_source_workbook(doc_path: Path) -> Path:
    """Writes a REAL workbook holding the exact values the golden plan writes.

    Phase D3.2 (§18) forbids fabricated source ranges. The golden plan is
    synthetic, so its source must be a real synthetic workbook rather than an
    invented address inside a real client file: every `source_cell_address` the
    plan cites resolves here and holds the planned value.
    """
    import openpyxl

    wb_path = doc_path.parent / "synthetic_source.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SYNTHETIC_SOURCE_SHEET
    row = 1
    for t_idx in sorted(GOLDEN_TABLES):
        initial, target, cols, label = GOLDEN_TABLES[t_idx]
        for i in range(target - initial):
            for c in range(cols):
                ws.cell(row=row, column=c + 1, value=f"{label} NEW R{i}C{c}")
            row += 1
    wb.save(str(wb_path))
    wb.close()
    return wb_path


def golden_source_address(t_idx: int, i: int, c: int) -> str:
    """The real cell in the synthetic workbook that backs one planned value."""
    import openpyxl

    row = 1
    for idx in sorted(GOLDEN_TABLES):
        initial, target, _cols, _label = GOLDEN_TABLES[idx]
        if idx == t_idx:
            return f"{openpyxl.utils.get_column_letter(c + 1)}{row + i}"
        row += target - initial
    raise KeyError(t_idx)


def build_golden_plan(
    manifest: RollForwardManifest,
    doc_path: Path,
    include_blocked: bool = False,
) -> MutationPlan:
    """Builds a version-locked MutationPlan over the four golden tables."""
    doc = Document(str(doc_path))
    source_wb = build_synthetic_source_workbook(doc_path)
    specs = []
    for t_idx in sorted(GOLDEN_TABLES):
        initial, target, cols, label = GOLDEN_TABLES[t_idx]
        table = doc.tables[t_idx]
        specs.append(
            TableMutationSpec(
                target_region_id=f"rfr-golden-{t_idx}",
                table_index=t_idx,
                table_hash=f"hash{t_idx}",
                operation="INSERT_ROWS",
                source_row_template_idx=1,
                initial_row_count=initial,
                target_row_count=target,
                insert_count=target - initial,
                expected_precondition_hash=FingerprintService.compute_table_semantic_fingerprint(table),
                expected_postcondition_hash="",
                row_mutations=[
                    RowMutationSpec(
                        row_idx=initial + i,
                        cells=[
                            CellMutationSpec(
                                col_idx=c,
                                source_doc_name=source_wb.name,
                                source_sheet=SYNTHETIC_SOURCE_SHEET,
                                source_cell_address=golden_source_address(t_idx, i, c),
                                value=f"{label} NEW R{i}C{c}",
                            )
                            for c in range(cols)
                        ],
                    )
                    for i in range(target - initial)
                ],
            )
        )

    if include_blocked:
        specs.append(
            TableMutationSpec(
                target_region_id="rfr-blocked-ambiguous",
                table_index=0,
                table_hash="hash0",
                initial_row_count=3,
                target_row_count=4,
                insert_count=1,
                expected_precondition_hash="",
                expected_postcondition_hash="",
                row_mutations=[
                    RowMutationSpec(
                        row_idx=3,
                        # Deliberately unaddressed: this region is blocked and must
                        # never reach execution, so it has no real source.
                        cells=[CellMutationSpec(col_idx=0, source_doc_name="unbound.xlsx",
                                                value="ILLEGAL")],
                    )
                ],
            )
        )

    return MutationPlan(
        manifest_id=manifest.manifest_id,
        manifest_version=manifest.manifest_version,
        target_doc_name=doc_path.name,
        table_mutations=specs,
    )


def build_request(
    manifest: RollForwardManifest,
    doc_path: Path,
    output_path: Path,
    plan: MutationPlan = None,
    **overrides,
) -> ExecutionRequest:
    """Assembles a fully-gated ExecutionRequest for the synthetic fixture."""
    kwargs = dict(
        manifest=manifest,
        mutation_plan=plan if plan is not None else build_golden_plan(manifest, doc_path),
        template_path=doc_path,
        output_path=output_path,
        source_paths=[],
        expected_source_hashes={},
        expected_approver=APPROVER,
    )
    kwargs.update(overrides)
    if "expected_template_hash" not in kwargs:
        kwargs["expected_template_hash"] = compute_file_sha256(doc_path)
    return ExecutionRequest(**kwargs)


# ============================================================================
# 0. SOURCE ADDRESSABILITY OF THE SYNTHETIC FIXTURE (Phase D3.2 §18)
# ============================================================================

def test_every_planned_source_address_resolves_to_a_real_cell(tmp_path, golden_doc,
                                                              approved_golden_manifest):
    """No fabricated source ranges: every cited address exists and holds its value."""
    import openpyxl

    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    wb_path = golden_doc.parent / "synthetic_source.xlsx"
    assert wb_path.exists(), "the plan must cite a source workbook that actually exists"

    wb = openpyxl.load_workbook(str(wb_path))
    try:
        for spec in plan.table_mutations:
            if spec.target_region_id == "rfr-blocked-ambiguous":
                continue  # deliberately unaddressed; never executes
            for row_mut in spec.row_mutations:
                for cell in row_mut.cells:
                    assert cell.source_sheet in wb.sheetnames
                    assert cell.source_cell_address
                    actual = wb[cell.source_sheet][cell.source_cell_address].value
                    assert actual == cell.value, (
                        f"{cell.source_doc_name}!{cell.source_sheet}!"
                        f"{cell.source_cell_address} holds {actual!r}, "
                        f"but the plan writes {cell.value!r}"
                    )
    finally:
        wb.close()


def test_golden_path_cells_pass_the_lineage_addressability_gate(tmp_path, golden_doc,
                                                                approved_golden_manifest):
    """The synthetic golden path is source-addressable, so it may publish."""
    from foundation.applications.rollforward.data_reconciliation import (
        SourceAddressability, SourceBindingLineageStatus,
    )

    output = tmp_path / "out" / "addressable.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.reconciliation.overall_status == ReconciliationStatus.MATCH.value
    assert report.reconciliation.blocked_items == 0

    cell_nodes = [n for n in report.lineage.nodes if n["type"] == "TARGET_CELL"]
    assert cell_nodes
    for node in cell_nodes:
        assert node["metadata"]["source_cell"], "every published cell must cite a source cell"
        assert node["metadata"]["source_sheet"] == SYNTHETIC_SOURCE_SHEET


# ============================================================================
# 1. COMPLETE GOLDEN-PATH EXECUTION
# ============================================================================

def test_golden_path_executes_all_four_golden_tables(tmp_path, golden_doc, approved_golden_manifest):
    """All four golden structural cases execute atomically and publish FINAL_VALIDATED."""
    output = tmp_path / "out" / "Generated_Golden.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )

    assert report.failure_detail == "" or report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.status == ExecutionStatus.COMPLETED
    assert report.publication_state == PublicationState.FINAL_VALIDATED
    assert output.exists()

    assert {r.region_id for r in report.executed_regions} == {
        f"rfr-golden-{i}" for i in GOLDEN_TABLES
    }
    assert len(report.structural_changes) == 4

    doc_out = Document(str(output))
    for t_idx, (initial, target, _cols, _label) in GOLDEN_TABLES.items():
        assert len(doc_out.tables[t_idx].rows) == target, f"table {t_idx}"

    changes = {c.table_index: c for c in report.structural_changes}
    for t_idx, (initial, target, _c, _l) in GOLDEN_TABLES.items():
        assert changes[t_idx].rows_before == initial
        assert changes[t_idx].rows_after == target
        assert changes[t_idx].rows_inserted == target - initial

    # The full lifecycle ran on the one and only RollForwardStateMachine.
    assert report.state_transitions == [
        "APPROVED->EXECUTING", "EXECUTING->VALIDATED", "VALIDATED->COMPLETED"
    ]
    assert report.execution_manifest_status == ManifestStatus.COMPLETED
    # The caller's governed manifest object is never mutated by execution.
    assert approved_golden_manifest.status == ManifestStatus.APPROVED

    assert report.validation_summary["is_valid"] is True
    assert report.validation_summary["failed"] == 0
    assert report.template_preserved is True
    assert report.rollback_occurred is False


# ============================================================================
# 2. APPROVAL GATING
# ============================================================================

def test_approval_gating_rejects_unapproved_manifest(tmp_path, golden_doc, approved_golden_manifest):
    """A manifest that is not APPROVED can never execute."""
    approved_golden_manifest.status = ManifestStatus.REVIEW_REQUIRED
    output = tmp_path / "out" / "unapproved.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )

    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.APPROVAL_MISSING
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert not output.exists()


def test_approval_gating_rejects_agent_and_system_approval(tmp_path, golden_doc, approved_golden_manifest):
    """Agent/system identities may never stand in for a human approver."""
    output = tmp_path / "out" / "agent_approved.docx"

    for fake_approver in ("agent", "system", "Claude"):
        approved_golden_manifest.approved_by = fake_approver
        report = RollForwardOrchestrator.execute(
            build_request(
                approved_golden_manifest, golden_doc, output, expected_approver=None
            )
        )
        assert report.status == ExecutionStatus.FAILED, fake_approver
        assert report.failure_code == FailureCode.APPROVAL_NOT_BY_USER, fake_approver
        assert not output.exists()


def test_approval_gating_rejects_non_user_transition_actor(tmp_path, golden_doc, approved_golden_manifest):
    """A hand-forged APPROVED transition recorded by a non-user actor is rejected."""
    approved_golden_manifest.history[-1].actor = "agent"
    output = tmp_path / "out" / "forged.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.failure_code == FailureCode.APPROVAL_NOT_BY_USER
    assert report.publication_state == PublicationState.NOT_PUBLISHED


def test_approval_gating_requires_timestamp(tmp_path, golden_doc, approved_golden_manifest):
    """Approval without a timestamp is not an approval."""
    approved_golden_manifest.approved_at = None
    output = tmp_path / "out" / "no_timestamp.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.failure_code == FailureCode.APPROVAL_MISSING


# ============================================================================
# 3. APPROVAL VERSION MISMATCH
# ============================================================================

def test_stale_approval_version_is_rejected(tmp_path, golden_doc, approved_golden_manifest):
    """An approval bound to an older manifest version is stale and blocks execution."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    approved_golden_manifest.manifest_version = 2  # manifest edited after approval
    output = tmp_path / "out" / "stale_approval.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.APPROVAL_VERSION_MISMATCH
    assert not output.exists()


def test_mutation_plan_version_mismatch_is_rejected(tmp_path, golden_doc, approved_golden_manifest):
    """A MutationPlan built against a different manifest version cannot execute."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    plan.manifest_version = 7
    output = tmp_path / "out" / "plan_mismatch.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.failure_code == FailureCode.PLAN_VERSION_MISMATCH
    assert report.publication_state == PublicationState.NOT_PUBLISHED


def test_post_approval_modification_invalidates_execution(tmp_path, golden_doc, approved_golden_manifest):
    """mark_modified() revokes approval, and the orchestrator honours that revocation."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    approved_golden_manifest.mark_modified(actor="user")
    output = tmp_path / "out" / "modified.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.APPROVAL_MISSING
    assert not output.exists()


# ============================================================================
# 4. STALE SOURCE REJECTION
# ============================================================================

def test_stale_source_aborts_before_any_mutation(tmp_path, golden_doc, approved_golden_manifest):
    """A source workbook that changed after planning aborts execution pre-mutation."""
    fake_source = tmp_path / "HMV-FA&RPT FY2024.xlsx"
    fake_source.write_bytes(b"planning-time content")
    frozen = SourceFreshnessTracker.snapshot_source_hashes([fake_source])

    fake_source.write_bytes(b"someone edited the workbook afterwards")

    output = tmp_path / "out" / "stale_source.docx"
    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, golden_doc, output,
            source_paths=[fake_source], expected_source_hashes=frozen,
        )
    )

    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.STALE_INPUT
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert not output.exists()
    # Aborted before mutation: nothing was staged and nothing rolled back.
    assert report.structural_changes == []
    assert report.reconciliation is None


def test_fresh_sources_pass_the_freshness_gate(tmp_path, golden_doc, approved_golden_manifest):
    """Unmodified sources satisfy the freshness gate and execution proceeds."""
    source = tmp_path / "HMV-FA&RPT FY2024.xlsx"
    source.write_bytes(b"planning-time content")
    frozen = SourceFreshnessTracker.snapshot_source_hashes([source])

    output = tmp_path / "out" / "fresh_source.docx"
    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, golden_doc, output,
            source_paths=[source], expected_source_hashes=frozen,
        )
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.source_hashes == frozen


# ============================================================================
# 5. STALE TEMPLATE REJECTION
# ============================================================================

def test_stale_template_aborts_and_does_not_rebuild_manifest(tmp_path, golden_doc, approved_golden_manifest):
    """A template that changed since manifest creation aborts with STALE_TEMPLATE."""
    output = tmp_path / "out" / "stale_template.docx"
    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, golden_doc, output,
            expected_template_hash="0" * 64,
        )
    )

    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.STALE_TEMPLATE
    assert "Re-run analysis/replanning explicitly" in report.failure_detail
    assert not output.exists()
    assert report.structural_changes == []


def test_missing_template_is_reported_explicitly(tmp_path, golden_doc, approved_golden_manifest):
    """A vanished template produces a structured failure, not an exception."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    missing = tmp_path / "does_not_exist.docx"
    output = tmp_path / "out" / "missing_template.docx"

    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, missing, output, plan=plan,
            expected_template_hash="",
        )
    )
    assert report.failure_code == FailureCode.TEMPLATE_NOT_FOUND


# ============================================================================
# 6. BLOCKED REGION EXCLUSION
# ============================================================================

def test_blocked_regions_are_excluded_and_stay_blocked(tmp_path, golden_doc, approved_golden_manifest):
    """UNKNOWN / MANUAL_REVIEW / AMBIGUOUS / MISSING regions are never executed."""
    output = tmp_path / "out" / "blocked.docx"
    plan = build_golden_plan(approved_golden_manifest, golden_doc, include_blocked=True)

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail

    excluded = {r.region_id: r for r in report.excluded_regions}
    assert excluded["rfr-blocked-unknown"].exclusion_reason == ExclusionReason.CLASSIFICATION_UNKNOWN
    assert excluded["rfr-blocked-manual"].exclusion_reason == ExclusionReason.CLASSIFICATION_MANUAL_REVIEW
    assert excluded["rfr-blocked-ambiguous"].exclusion_reason == ExclusionReason.SOURCE_BINDING_AMBIGUOUS
    assert excluded["rfr-blocked-missing"].exclusion_reason == ExclusionReason.SOURCE_BINDING_MISSING

    # Every excluded region carries region_id, classification, reason and status.
    for rec in report.excluded_regions:
        assert rec.region_id
        assert rec.exclusion_reason is not None
        assert rec.reason_detail
        assert rec.status.value == "EXCLUDED"

    # The ambiguous region was in the approved plan and targeted table 0 -- it
    # must still be untouched in the published output.
    doc_out = Document(str(output))
    assert len(doc_out.tables[0].rows) == 3
    assert doc_out.tables[0].rows[2].cells[0].text.strip() == "Untouched 3"

    assert report.unresolved_blocked_summary["CLASSIFICATION_UNKNOWN"] == 1
    assert report.unresolved_blocked_summary["SOURCE_BINDING_AMBIGUOUS"] == 1


def test_plan_targeting_a_region_outside_the_manifest_is_excluded(
    tmp_path, golden_doc, approved_golden_manifest
):
    """A MutationPlan may not introduce targets the approved manifest never declared."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    plan.table_mutations[0].target_region_id = "rfr-never-declared"
    output = tmp_path / "out" / "unknown_region.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    excluded = {r.region_id: r for r in report.excluded_regions}
    assert excluded["rfr-never-declared"].exclusion_reason == ExclusionReason.REGION_NOT_IN_MANIFEST
    # Table 1 was never mutated because its region is no longer plan-covered.
    doc_out = Document(str(output))
    assert len(doc_out.tables[1].rows) == GOLDEN_TABLES[1][0]


def test_plan_pointing_at_the_wrong_table_is_excluded(tmp_path, golden_doc, approved_golden_manifest):
    """The plan's table index must agree with the manifest region's row-template anchor."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    plan.table_mutations[0].table_index = 4  # region rfr-golden-1 anchors to table 1

    scope = MutationScopeResolver.resolve(approved_golden_manifest, plan)
    excluded = {r.region_id: r for r in scope.excluded_records}
    assert excluded["rfr-golden-1"].exclusion_reason == ExclusionReason.PLAN_TARGET_MISMATCH


def test_row_deletion_plan_is_excluded_as_unsupported(tmp_path, golden_doc, approved_golden_manifest):
    """A plan implying row deletion is excluded, never best-effort executed."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    plan.table_mutations[0].target_row_count = 1  # below initial_row_count of 2

    scope = MutationScopeResolver.resolve(approved_golden_manifest, plan)
    excluded = {r.region_id: r for r in scope.excluded_records}
    assert excluded["rfr-golden-1"].exclusion_reason == ExclusionReason.UNSUPPORTED_OPERATION
    assert "row deletion" in excluded["rfr-golden-1"].reason_detail


def test_execution_fails_when_no_region_is_executable(tmp_path, golden_doc, approved_golden_manifest):
    """A plan containing only blocked regions produces NO_EXECUTABLE_REGIONS."""
    plan = MutationPlan(
        manifest_id=approved_golden_manifest.manifest_id,
        manifest_version=approved_golden_manifest.manifest_version,
        target_doc_name=golden_doc.name,
        table_mutations=[
            TableMutationSpec(
                target_region_id="rfr-blocked-unknown",
                table_index=0,
                table_hash="hash0",
                initial_row_count=3,
                target_row_count=4,
                insert_count=1,
                expected_precondition_hash="",
                expected_postcondition_hash="",
            )
        ],
    )
    output = tmp_path / "out" / "nothing.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.failure_code == FailureCode.NO_EXECUTABLE_REGIONS
    assert not output.exists()


# ============================================================================
# 7. FULL-DOCUMENT PERCEPTION VALIDATION
# ============================================================================

def test_full_document_perception_validation_covers_whole_document(
    tmp_path, golden_doc, approved_golden_manifest
):
    """Validation is document-wide: all nine categories run, not just the target tables."""
    output = tmp_path / "out" / "perception.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail

    by_category = report.validation_summary["by_category"]
    for category in ValidationCategory:
        assert category.value in by_category, category
        assert by_category[category.value]["failed"] == 0

    # Re-run the gate directly against the published artifact for independent proof.
    baseline = DocumentBaseline.capture(golden_doc, sorted(GOLDEN_TABLES))
    validation = FullDocumentValidator.validate(
        baseline,
        output,
        [
            ExpectedMutation(
                region_id=f"rfr-golden-{t}",
                table_index=t,
                baseline_row_count=GOLDEN_TABLES[t][0],
                expected_row_count=GOLDEN_TABLES[t][1],
                expected_inserted_rows=GOLDEN_TABLES[t][1] - GOLDEN_TABLES[t][0],
            )
            for t in sorted(GOLDEN_TABLES)
        ],
    )
    assert validation.is_valid is True
    perception_checks = [
        c for c in validation.checks if c.category == ValidationCategory.PERCEPTION
    ]
    assert perception_checks
    assert all(c.status == CheckStatus.PASSED for c in perception_checks)


def test_validator_rejects_a_corrupt_package(tmp_path, golden_doc):
    """A non-OOXML artifact fails at the package gate rather than anywhere later."""
    baseline = DocumentBaseline.capture(golden_doc, [1])
    corrupt = tmp_path / "corrupt.docx"
    corrupt.write_bytes(b"this is definitely not a zip package")

    validation = FullDocumentValidator.validate(baseline, corrupt, [])
    assert validation.is_valid is False
    assert any(c.check_id == "PKG-002" and c.status == CheckStatus.FAILED for c in validation.checks)


# ============================================================================
# 8. NON-TARGET SEMANTIC INTEGRITY
# ============================================================================

def test_non_target_regions_have_zero_semantic_drift(tmp_path, golden_doc, approved_golden_manifest):
    """Every non-target table and paragraph is byte-for-byte semantically identical."""
    output = tmp_path / "out" / "non_target.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.validation_summary["by_category"]["NON_TARGET_INTEGRITY"]["failed"] == 0

    doc_before, doc_after = Document(str(golden_doc)), Document(str(output))
    before_fp = FingerprintService.compute_document_non_target_fingerprint(
        doc_before, set(GOLDEN_TABLES)
    )
    after_fp = FingerprintService.compute_document_non_target_fingerprint(
        doc_after, set(GOLDEN_TABLES)
    )
    assert before_fp == after_fp
    assert [p.text for p in doc_before.paragraphs] == [p.text for p in doc_after.paragraphs]


def test_undeclared_drift_fails_validation(tmp_path, golden_doc):
    """A change to a non-target table with no ExpectedMutation is a hard failure."""
    baseline = DocumentBaseline.capture(golden_doc, [1])

    drifted = tmp_path / "drifted.docx"
    shutil.copyfile(str(golden_doc), str(drifted))
    doc = Document(str(drifted))
    doc.tables[0].rows[1].cells[0].text = "SILENTLY CHANGED"
    doc.save(str(drifted))

    validation = FullDocumentValidator.validate(baseline, drifted, [])
    assert validation.is_valid is False
    failed_ids = {c.check_id for c in validation.checks if c.status == CheckStatus.FAILED}
    assert "NTI-001" in failed_ids
    assert "NTI-002" in failed_ids


# ============================================================================
# 9. PARTIAL EXECUTION ROLLBACK
# ============================================================================

def test_partial_execution_rolls_back_entirely(tmp_path, golden_doc, approved_golden_manifest):
    """T10 and T13 succeed, T14 fails, T15 never commits -- the whole run is discarded."""
    output = tmp_path / "out" / "partial.docx"
    template_hash_before = compute_file_sha256(golden_doc)

    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    # Table 14 (index 3) declares a row count the supplied mutations cannot reach.
    t14_spec = next(s for s in plan.table_mutations if s.table_index == 3)
    t14_spec.target_row_count = 99

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )

    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.STRUCTURAL_MUTATION_FAILED
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert report.rollback_occurred is True
    assert report.staging_discarded is True
    assert report.output_hash is None

    # No partial artifact, no leftover staging directory, original template intact.
    assert not output.exists()
    assert not list(output.parent.glob(".d3_staging_*"))
    assert compute_file_sha256(golden_doc) == template_hash_before
    assert report.template_preserved is True

    doc_tmpl = Document(str(golden_doc))
    for t_idx, (initial, _t, _c, _l) in GOLDEN_TABLES.items():
        assert len(doc_tmpl.tables[t_idx].rows) == initial

    assert report.execution_manifest_status == ManifestStatus.FAILED


def test_rollback_leaves_a_previously_published_output_untouched(
    tmp_path, golden_doc, approved_golden_manifest
):
    """A failing re-run never overwrites or corrupts an existing validated artifact."""
    output = tmp_path / "out" / "existing.docx"
    first = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert first.status == ExecutionStatus.COMPLETED, first.failure_detail
    published_hash = compute_file_sha256(output)

    bad_plan = build_golden_plan(approved_golden_manifest, golden_doc)
    next(s for s in bad_plan.table_mutations if s.table_index == 3).target_row_count = 99
    bad_plan.plan_id = "plan-deliberately-broken"

    second = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=bad_plan)
    )
    assert second.status == ExecutionStatus.FAILED
    assert compute_file_sha256(output) == published_hash


# ============================================================================
# 10. IDEMPOTENT SECOND EXECUTION
# ============================================================================

def test_second_identical_execution_is_a_noop(tmp_path, golden_doc, approved_golden_manifest):
    """Re-running the same approved execution detects the applied state and no-ops."""
    output = tmp_path / "out" / "idempotent.docx"
    plan = build_golden_plan(approved_golden_manifest, golden_doc)

    first = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert first.status == ExecutionStatus.COMPLETED, first.failure_detail
    first_hash = first.output_hash

    second = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert second.status == ExecutionStatus.NOOP
    assert second.idempotent_noop is True
    assert second.publication_state == PublicationState.FINAL_VALIDATED
    assert second.output_hash == first_hash
    assert "already applied" in second.failure_detail

    # No duplicate mutation: row counts are unchanged after the second run.
    doc_out = Document(str(output))
    for t_idx, (_i, target, _c, _l) in GOLDEN_TABLES.items():
        assert len(doc_out.tables[t_idx].rows) == target
    assert compute_file_sha256(output) == first_hash


def test_a_different_plan_is_not_treated_as_idempotent(tmp_path, golden_doc, approved_golden_manifest):
    """The idempotence ledger is keyed on the exact plan digest, not just the path."""
    output = tmp_path / "out" / "ledger.docx"
    first = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert first.status == ExecutionStatus.COMPLETED, first.failure_detail

    ledger = ExecutionLedger.load(output)
    assert ledger is not None
    assert ledger.output_hash == first.output_hash
    assert ledger.manifest_version == approved_golden_manifest.manifest_version

    different = build_golden_plan(approved_golden_manifest, golden_doc)
    different.table_mutations[0].row_mutations[0].cells[0].value = "A DIFFERENT VALUE"

    second = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=different)
    )
    assert second.status != ExecutionStatus.NOOP
    assert second.idempotent_noop is False


# ============================================================================
# 11. D2 RECONCILIATION FAILURE
# ============================================================================

def _mismatch_summary(manifest_id, manifest_version, session_id, status):
    return ManifestReconciliationSummary(
        manifest_id=manifest_id,
        manifest_version=manifest_version,
        session_id=session_id,
        total_tables=4,
        total_cells=10,
        matched_cells=7,
        mismatched_cells=3,
        missing_cells=0,
        type_mismatches=0,
        format_mismatches=0,
        manual_review_items=0,
        blocked_items=0,
        source_freshness_verified=True,
        reperception_verified=True,
        overall_status=status,
        reconciled_at="2026-08-23T00:00:00+00:00",
    )


@pytest.mark.parametrize(
    "status",
    [
        ReconciliationStatus.MISMATCH,
        ReconciliationStatus.TYPE_MISMATCH,
        ReconciliationStatus.MISSING_OUTPUT,
        ReconciliationStatus.TRANSFORMATION_MISMATCH,
        ReconciliationStatus.STALE_INPUT,
    ],
)
def test_reconciliation_failure_blocks_publication(
    tmp_path, golden_doc, approved_golden_manifest, monkeypatch, status
):
    """Every hard D2 status discards the artifact instead of publishing it."""
    output = tmp_path / "out" / f"recon_{status.value}.docx"

    def _stub(cls, manifest, mutation_plan, doc_output_path, source_paths, source_hashes):
        return _mismatch_summary(
            manifest.manifest_id, manifest.manifest_version, manifest.session_id, status
        )

    monkeypatch.setattr(
        orch_module.DataReconciliationEngine,
        "reconcile_document_output",
        classmethod(_stub),
    )

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.DATA_RECONCILIATION_FAILED
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert not output.exists()
    assert report.rollback_occurred is True
    assert report.reconciliation is not None
    assert report.reconciliation.overall_status == status.value


def test_reconciliation_manual_review_withholds_publication(
    tmp_path, golden_doc, approved_golden_manifest, monkeypatch
):
    """Unresolved manual-review items yield REQUIRES_MANUAL_REVIEW, never a published artifact."""
    output = tmp_path / "out" / "recon_manual.docx"

    def _stub(cls, manifest, mutation_plan, doc_output_path, source_paths, source_hashes):
        return _mismatch_summary(
            manifest.manifest_id, manifest.manifest_version, manifest.session_id,
            ReconciliationStatus.MANUAL_REVIEW,
        )

    monkeypatch.setattr(
        orch_module.DataReconciliationEngine,
        "reconcile_document_output",
        classmethod(_stub),
    )

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.REQUIRES_MANUAL_REVIEW
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert report.failure_code == FailureCode.DATA_RECONCILIATION_MANUAL_REVIEW
    assert not output.exists()
    assert report.execution_manifest_status == ManifestStatus.REQUIRES_MANUAL_REVIEW


def test_reconciliation_runs_after_mutation_and_matches(tmp_path, golden_doc, approved_golden_manifest):
    """On the golden path, D2 reconciles every populated target cell against its source."""
    output = tmp_path / "out" / "recon_ok.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail

    rec = report.reconciliation
    assert rec is not None
    assert rec.overall_status == ReconciliationStatus.MATCH.value
    assert rec.total_cells == rec.matched_cells > 0
    assert rec.mismatched_cells == 0
    assert rec.missing_cells == 0
    assert len(rec.per_table) == 4
    # The digest carries counts only -- never document plaintext.
    assert all("value" not in key for t in rec.per_table for key in t)


# ============================================================================
# 12. OUTPUT HASH GENERATION
# ============================================================================

def test_output_hash_identifies_the_validated_artifact(tmp_path, golden_doc, approved_golden_manifest):
    """The recorded output_hash is the SHA256 of exactly the published bytes."""
    output = tmp_path / "out" / "hashed.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.output_hash == compute_file_sha256(output)
    assert len(report.output_hash) == 64
    assert report.template_hash == compute_file_sha256(golden_doc)
    assert report.output_hash != report.template_hash


def test_no_output_hash_when_nothing_is_published(tmp_path, golden_doc, approved_golden_manifest):
    """A failed execution never records an output hash."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    next(s for s in plan.table_mutations if s.table_index == 3).target_row_count = 99
    output = tmp_path / "out" / "no_hash.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.output_hash is None


# ============================================================================
# 13. LINEAGE COMPLETENESS
# ============================================================================

def test_lineage_chain_is_complete_and_redacted(tmp_path, golden_doc, approved_golden_manifest):
    """The lineage spans source document -> ... -> validation result, without plaintext."""
    source = tmp_path / "HMV-FA&RPT FY2024.xlsx"
    source.write_bytes(b"source workbook bytes")
    frozen = SourceFreshnessTracker.snapshot_source_hashes([source])

    output = tmp_path / "out" / "lineage.docx"
    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, golden_doc, output,
            source_paths=[source], expected_source_hashes=frozen,
        )
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail

    lineage = report.lineage
    assert lineage is not None
    node_types = set(lineage.chain_kinds())
    for required in (
        "SOURCE_DOCUMENT", "SOURCE_BINDING", "MANIFEST_VERSION", "MUTATION_PLAN",
        "EXECUTION", "TARGET_REGION", "TARGET_CELL", "GENERATED_DOCUMENT", "VALIDATION_RESULT",
    ):
        assert required in node_types, required

    node_ids = {n["id"] for n in lineage.nodes}
    for edge in lineage.edges:
        assert edge["from"] in node_ids
        assert edge["to"] in node_ids

    # Cell nodes carry digests, never document plaintext.
    cell_nodes = [n for n in lineage.nodes if n["type"] == "TARGET_CELL"]
    assert cell_nodes
    for node in cell_nodes:
        assert node["metadata"]["value_digest"].startswith("sha256:")
        assert "Table 10 NEW" not in str(node)

    doc_node = next(n for n in lineage.nodes if n["type"] == "GENERATED_DOCUMENT")
    assert doc_node["metadata"]["output_hash"] == report.output_hash

    manifest_node = next(n for n in lineage.nodes if n["type"] == "MANIFEST_VERSION")
    assert manifest_node["metadata"]["approver"] == APPROVER
    assert manifest_node["metadata"]["manifest_version"] == approved_golden_manifest.manifest_version


def test_execution_report_carries_every_required_field(tmp_path, golden_doc, approved_golden_manifest):
    """The RollForwardExecutionReport satisfies the Phase D3 §16 field contract."""
    output = tmp_path / "out" / "report_fields.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail

    payload = report.to_json_dict()
    for field in (
        "execution_id", "manifest_id", "manifest_version", "approver", "approved_at",
        "source_hashes", "template_hash", "started_at", "ended_at", "executed_regions",
        "excluded_regions", "structural_changes", "reconciliation", "validation_summary",
        "rollback_occurred", "output_hash", "status", "publication_state", "lineage",
    ):
        assert field in payload, field

    assert payload["execution_id"].startswith("exec-")
    assert payload["started_at"] < payload["ended_at"]
    # No document plaintext leaked into the serialized report.
    assert "Table 10 NEW" not in str(payload)


# ============================================================================
# 14. GROUND TRUTH EVALUATION INDEPENDENCE
# ============================================================================

def test_ground_truth_evaluation_does_not_alter_execution(tmp_path, golden_doc, approved_golden_manifest):
    """Ground Truth is read after the fact and cannot change state or output bytes."""
    ground_truth = tmp_path / "ground_truth.docx"
    gt_doc = Document()
    gt_doc.add_heading("Ground Truth", level=1)
    gt = gt_doc.add_table(rows=12, cols=3)
    for c in range(3):
        gt.rows[0].cells[c].text = f"Table 10 Col {c}"
    gt_doc.save(str(ground_truth))

    output = tmp_path / "out" / "gt.docx"
    report = RollForwardOrchestrator.execute(
        build_request(
            approved_golden_manifest, golden_doc, output, ground_truth_path=ground_truth
        )
    )

    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.publication_state == PublicationState.FINAL_VALIDATED

    gt_report = report.ground_truth_evaluation
    assert gt_report is not None and gt_report.evaluated is True
    assert gt_report.ground_truth_sha256 == compute_file_sha256(ground_truth)

    # Ground Truth disagrees with the generated artifact and says so honestly...
    subjects = {f.subject: f for f in gt_report.findings}
    assert subjects["table[1].rows"].status == GroundTruthFindingStatus.CONTRADICTED
    assert subjects["document.table_count"].status == GroundTruthFindingStatus.CONTRADICTED
    # ...while the execution outcome and published bytes are provably unaffected.
    assert report.output_hash == compute_file_sha256(output)
    assert Document(str(output)).tables[1].rows[0].cells[0].text == "Table 10 Col 0"
    assert len(Document(str(output)).tables[1].rows) == GOLDEN_TABLES[1][1]


def test_execution_succeeds_without_any_ground_truth(tmp_path, golden_doc, approved_golden_manifest):
    """Ground Truth is optional; nothing in the pipeline depends on it."""
    output = tmp_path / "out" / "no_gt.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, ground_truth_path=None)
    )
    assert report.status == ExecutionStatus.COMPLETED, report.failure_detail
    assert report.publication_state == PublicationState.FINAL_VALIDATED
    assert report.ground_truth_evaluation is None


def test_ground_truth_evaluator_grades_all_four_statuses(tmp_path, golden_doc):
    """The evaluator distinguishes VERIFIED / CONTRADICTED / INFERRED honestly."""
    generated = tmp_path / "gen.docx"
    shutil.copyfile(str(golden_doc), str(generated))

    identical = tmp_path / "identical_gt.docx"
    shutil.copyfile(str(golden_doc), str(identical))

    report = GroundTruthEvaluator.evaluate(
        generated,
        identical,
        [ExpectedMutation(
            region_id="rfr-golden-1", table_index=1,
            baseline_row_count=2, expected_row_count=2, expected_inserted_rows=0,
        )],
    )
    statuses = {f.subject: f.status for f in report.findings}
    assert statuses["document.table_count"] == GroundTruthFindingStatus.VERIFIED
    assert statuses["table[1].rows"] == GroundTruthFindingStatus.VERIFIED

    empty_gt = tmp_path / "empty_gt.docx"
    Document().save(str(empty_gt))
    report2 = GroundTruthEvaluator.evaluate(
        generated,
        empty_gt,
        [ExpectedMutation(
            region_id="rfr-golden-1", table_index=1,
            baseline_row_count=2, expected_row_count=2, expected_inserted_rows=0,
        )],
    )
    statuses2 = {f.subject: f.status for f in report2.findings}
    assert statuses2["document.table_count"] == GroundTruthFindingStatus.CONTRADICTED
    assert statuses2["table[1].rows"] == GroundTruthFindingStatus.INFERRED


# ============================================================================
# 15. FINAL_VALIDATED PUBLICATION GATE
# ============================================================================

def test_full_validation_failure_blocks_final_validated(
    tmp_path, golden_doc, approved_golden_manifest, monkeypatch
):
    """A failing hard validation rule withholds publication even after a clean mutation."""
    output = tmp_path / "out" / "gated.docx"

    def _invalid(cls, baseline, output_path, expected_mutations):
        rpt = FullDocumentValidationReport(is_valid=False)
        rpt.hard_failures.append("[TEST-001] Injected hard validation failure.")
        return rpt

    monkeypatch.setattr(orch_module.FullDocumentValidator, "validate", classmethod(_invalid))

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )
    assert report.status == ExecutionStatus.FAILED
    assert report.failure_code == FailureCode.FULL_VALIDATION_FAILED
    assert report.publication_state == PublicationState.NOT_PUBLISHED
    assert not output.exists()
    assert report.output_hash is None
    assert report.rollback_occurred is True


def test_final_validated_requires_completed_and_every_hard_gate(
    tmp_path, golden_doc, approved_golden_manifest
):
    """FINAL_VALIDATED is published only when status is COMPLETED and all gates pass."""
    output = tmp_path / "out" / "gate_ok.docx"
    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output)
    )

    assert report.status == ExecutionStatus.COMPLETED
    assert report.validation_summary["is_valid"] is True
    assert report.validation_summary["failed"] == 0
    assert report.reconciliation.overall_status == ReconciliationStatus.MATCH.value
    assert report.publication_state == PublicationState.FINAL_VALIDATED
    assert output.exists()
    assert ExecutionLedger.load(output) is not None


def test_no_ledger_is_written_for_a_failed_execution(tmp_path, golden_doc, approved_golden_manifest):
    """A failed run leaves no publication ledger behind to fake idempotence with."""
    plan = build_golden_plan(approved_golden_manifest, golden_doc)
    next(s for s in plan.table_mutations if s.table_index == 3).target_row_count = 99
    output = tmp_path / "out" / "no_ledger.docx"

    report = RollForwardOrchestrator.execute(
        build_request(approved_golden_manifest, golden_doc, output, plan=plan)
    )
    assert report.status == ExecutionStatus.FAILED
    assert ExecutionLedger.load(output) is None


# ============================================================================
# 16. REAL FIXTURE END-TO-END ACCEPTANCE
# ============================================================================

def test_real_fixture_end_to_end_acceptance(tmp_path):
    """Full workflow on FY2023 Local File + Template + FY2024 FA&RPT + Appendix I.

    Phase D3.2 (P0-4) HISTORICAL REASON
    -----------------------------------
    This test originally asserted COMPLETED / FINAL_VALIDATED with
    "72 / 72 cells matched". The Phase D3.1 audit established that not one of
    those 72 cells carried a source cell address, so the figure measured
    plan-to-output fidelity while being presented as source-to-output
    traceability. Under the LineageAddressabilityGate the same run is now
    withheld from publication.

    The test is kept and strengthened rather than deleted: it still exercises
    the entire orchestrated pipeline and asserts that the ENGINE MECHANICS are
    sound (structural mutation, full-document validation, transaction, exclusion
    reporting) while the artifact is correctly NOT published because its plan
    cannot be traced to real source cells.

    It writes no artifacts: the historical Phase D3 report is preserved on disk
    under its INVALIDATED_FOR_PLANNING_CONTAMINATION banner.
    """
    from foundation.applications.rollforward.data_reconciliation import (
        SourceAddressability,
    )
    from foundation.tests.evaluation.rollforward_d3_execution import (
        build_execution_request,
    )

    output = tmp_path / "Generated_LocalFile_FY2024_PhaseD3_gated.docx"
    request, manifest, _targets = build_execution_request(
        output_path=output, with_ground_truth=True
    )
    report = orch_module.RollForwardOrchestrator.execute(request)

    # --- the gate holds: nothing is published --------------------------------
    assert report.status.value == "REQUIRES_MANUAL_REVIEW", report.failure_detail
    assert report.publication_state.value == "NOT_PUBLISHED"
    assert report.failure_code.value == "DATA_RECONCILIATION_MANUAL_REVIEW"
    assert not output.exists(), "an artifact whose cells are not source-addressable must not publish"
    assert report.output_hash is None
    assert ExecutionLedger.load(output) is None
    assert report.rollback_occurred is True
    assert report.template_preserved is True

    # --- the reason is addressability, not a value error ---------------------
    assert report.reconciliation.overall_status == "BLOCKED"
    assert report.reconciliation.mismatched_cells == 0
    assert report.reconciliation.missing_cells == 0
    assert report.reconciliation.blocked_items == report.reconciliation.total_cells

    # --- the mechanics still work --------------------------------------------
    executed = {r.region_id for r in report.executed_regions}
    assert executed == {"rfr-071", "rfr-098", "rfr-101"}
    changes = {c.table_index: c for c in report.structural_changes}
    assert (changes[10].rows_before, changes[10].rows_after) == (6, 11)
    assert (changes[14].rows_before, changes[14].rows_after) == (8, 10)
    assert (changes[15].rows_before, changes[15].rows_after) == (7, 16)
    assert report.validation_summary["is_valid"] is True
    assert report.validation_summary["failed"] == 0

    # --- blocked Phase C regions still stay blocked ---------------------------
    excluded = {r.region_id: r for r in report.excluded_regions}
    assert excluded["rfr-093"].exclusion_reason.value == "UNSUPPORTED_OPERATION"
    assert len(report.excluded_regions) == len(manifest.regions) - len(report.executed_regions)
    assert report.unresolved_blocked_summary.get("CLASSIFICATION_UNKNOWN", 0) > 0

    # --- lineage records the addressability verdict ---------------------------
    cell_nodes = [n for n in report.lineage.nodes if n["type"] == "TARGET_CELL"]
    assert cell_nodes
    assert all(n["metadata"]["source_cell"] is None for n in cell_nodes), (
        "the Phase D3 harness plan names no cell address on any table; that is "
        "precisely why this run cannot publish"
    )

    # --- the historical, contaminated report is untouched ---------------------
    historical = REPO_ROOT / "docs/evaluation/LocalFile_RollForward_D3_Execution_Report.md"
    if historical.exists():
        assert "INVALIDATED_FOR_PLANNING_CONTAMINATION" in historical.read_text(encoding="utf-8")


def test_real_fixture_run_is_stable_and_writes_no_ledger(tmp_path):
    """A run that cannot publish must not become idempotent-NOOP on a re-run.

    Phase D3.2 (P0-4) HISTORICAL REASON
    -----------------------------------
    This replaces a test that asserted the second real-fixture execution
    returned NOOP. That behaviour depended on the first execution publishing,
    which the addressability gate now correctly prevents. Idempotence itself is
    still covered end-to-end by the synthetic golden-path tests
    (`test_second_identical_execution_is_a_noop`), whose plan IS source-addressable.
    """
    from foundation.tests.evaluation.rollforward_d3_execution import build_execution_request

    output = tmp_path / "Generated_LocalFile_FY2024_PhaseD3_stability.docx"
    request, _manifest, _targets = build_execution_request(
        output_path=output, with_ground_truth=False
    )

    first = orch_module.RollForwardOrchestrator.execute(request)
    second = orch_module.RollForwardOrchestrator.execute(request)

    assert first.status.value == "REQUIRES_MANUAL_REVIEW"
    assert second.status.value == "REQUIRES_MANUAL_REVIEW"
    assert second.idempotent_noop is False, (
        "a run that never published must not be mistaken for an already-applied one"
    )
    assert not output.exists()
    assert ExecutionLedger.load(output) is None
    assert first.reconciliation.overall_status == second.reconciliation.overall_status == "BLOCKED"

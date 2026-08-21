"""
Unit Tests for Local File Roll-Forward Domain Models & State Machine (V1 Contract)
==================================================================================
Location: foundation/tests/test_rollforward_domain.py

Verifies:
- Pydantic schema validation & roundtrip JSON serialization
- Real-world fixture table growth manifests (2->11 rows, 6->10 rows, 10->16 rows)
- Review gating & execution gate semantics
- Strict user-only approval provenance
- Invalidation of approval on post-approval modification
- Rejection of stale/ambiguous source bindings
- Rejection of illegal lifecycle transitions
"""
from __future__ import annotations

import json
import pytest

from applications.rollforward.models import (
    ManifestStatus,
    RegionClassification,
    SourceBindingStatus,
    SourceType,
    ExecutionGate,
    ValidationRuleType,
    ValidationSeverity,
    DiffChangeType,
    GroundTruthStatus,
    HistoricalReference,
    SourceBinding,
    StructuralDelta,
    RowTemplate,
    FigureBinding,
    ValidationRule,
    RollForwardDiff,
    RollForwardRegion,
    TransitionLog,
    RollForwardManifest,
)
from applications.rollforward.state_machine import (
    RollForwardStateMachine,
    IllegalTransitionError,
    UnauthorizedApprovalError,
    ApprovalInvalidationError,
)


def test_manifest_serialization_deserialization_roundtrip():
    """Verify full JSON round-trip serialization of RollForwardManifest."""
    manifest = RollForwardManifest(
        session_id="session-test-001",
        historical_document_id="doc-hist-fy2023",
        template_document_id="doc-tmpl-decree20",
        current_source_document_ids=["doc-farpt-fy2024", "doc-app1-fy2024"],
        status=ManifestStatus.DISCOVERED,
        regions=[
            RollForwardRegion(
                region_id="rfr-test-1",
                section_name="Preamble: Company Profile",
                target_document_id="doc-tmpl-decree20",
                target_element_ids=["table-0-cell-0-0"],
                classification=RegionClassification.UPDATE,
                current_sources=[
                    SourceBinding(
                        source_doc_id="doc-farpt-fy2024",
                        source_doc_name="HMV-FA&RPT FY2024.xlsx",
                        source_type=SourceType.XLSX,
                        sheet_name="I. Related parties",
                        cell_address="B3",
                        match_basis=["company_legal_name"],
                        status=SourceBindingStatus.VERIFIED,
                        reason="Audited legal name of taxpayer",
                    )
                ],
                mutation_strategy="SCALAR_CELL_REPLACE",
            )
        ],
    )

    json_str = manifest.model_dump_json()
    data = json.loads(json_str)

    assert data["schema_version"] == "1.0.0"
    assert data["manifest_version"] == 1
    assert data["session_id"] == "session-test-001"
    assert len(data["regions"]) == 1
    assert data["regions"][0]["classification"] == "UPDATE"

    restored = RollForwardManifest.model_validate_json(json_str)
    assert restored.manifest_id == manifest.manifest_id
    assert restored.regions[0].current_sources[0].cell_address == "B3"


def test_real_table_10_growth_manifest():
    """Verify Table 10 (Financial Ratios): 2 -> 11 rows growth (+9 rows)."""
    region = RollForwardRegion(
        region_id="rfr-table-10-ratios",
        section_name="Section 6: Financial Analysis",
        target_document_id="doc-tmpl-decree20",
        target_element_ids=["table-10-hash-2bd8b27f"],
        classification=RegionClassification.REPEATABLE,
        historical_reference=HistoricalReference(
            doc_id="doc-hist-fy2023",
            table_index=10,
            value_snippet="Financial Ratios Table",
            ground_truth_status=GroundTruthStatus.VERIFIED,
        ),
        current_sources=[
            SourceBinding(
                source_doc_id="doc-farpt-fy2024",
                source_doc_name="HMV-FA&RPT FY2024.xlsx",
                source_type=SourceType.XLSX,
                sheet_name="Financial Analysis",
                cell_range="A4:D35",
                match_basis=["multi_year_financial_ratios", "audited_financials"],
                status=SourceBindingStatus.VERIFIED,
                reason="Audited 3-year weighted average metrics from FA&RPT",
            )
        ],
        structural_delta=StructuralDelta(
            template_rows=6,
            target_rows=11,
            insert_count=9,
            delete_count=0,
            column_delta=0,
            merge_topology_changed=False,
            row_template_anchor="table:10:2bd8b27f_row:1",
            observation_source="audit_comparison_gt_fy2024",
            observation_context={"historical_rows": 2, "gt_rows": 11},
        ),
        row_template=RowTemplate(
            template_row_idx=1,
            row_anchor="table:10:2bd8b27f_row:1",
            cell_properties_policy="INHERIT_PROTOTYPE",
            merge_policy="RESET_VMERGE_RETAIN_GRIDSPAN",
            safe_to_clone=True,
        ),
        validation_rules=[
            ValidationRule(
                rule_type=ValidationRuleType.ROW_COUNT_MATCH,
                severity=ValidationSeverity.BLOCKER,
                parameters={"expected_rows": 11},
                description="Verify table expands to exactly 11 rows",
            ),
            ValidationRule(
                rule_type=ValidationRuleType.ARITHMETIC_CONSTRAINT,
                severity=ValidationSeverity.BLOCKER,
                parameters={"equation": "Net Cost Plus = Operating Profit / Total Costs"},
                description="Validate ratio computation consistency",
            ),
        ],
        mutation_strategy="CLONE_ROW_AND_POPULATE",
    )

    assert region.classification == RegionClassification.REPEATABLE
    assert region.structural_delta.insert_count == 9
    assert region.row_template.safe_to_clone is True
    assert region.execution_gate == ExecutionGate.READY
    assert region.requires_manual_review() is False


def test_real_table_14_growth_manifest():
    """Verify Table 14 (Comparable Companies List): 6 -> 10 rows growth (+4 rows)."""
    region = RollForwardRegion(
        region_id="rfr-table-14-comparables",
        section_name="Section 7: Benchmarking Analysis",
        target_document_id="doc-tmpl-decree20",
        target_element_ids=["table-14-hash-515cf63c"],
        classification=RegionClassification.REPEATABLE,
        current_sources=[
            SourceBinding(
                source_doc_id="doc-bm-fy2024",
                source_doc_name="HMV-25-Draft BM FY24-W1203.xlsb",
                source_type=SourceType.XLSX,
                sheet_name="Final Set",
                cell_range="A5:F15",
                match_basis=["peer_group_companies"],
                status=SourceBindingStatus.VERIFIED,
                reason="Updated accepted comparable company list",
            )
        ],
        structural_delta=StructuralDelta(
            template_rows=8,
            target_rows=10,
            insert_count=4,
            delete_count=0,
            row_template_anchor="table:14:515cf63c_row:1",
            observation_source="benchmarking_refresh_fy2024",
        ),
        mutation_strategy="CLONE_ROW_AND_POPULATE",
    )

    assert region.structural_delta.insert_count == 4
    assert region.execution_gate == ExecutionGate.READY


def test_real_table_15_growth_manifest():
    """Verify Table 15 (Benchmarking Quartiles): 10 -> 16 rows growth (+6 rows)."""
    region = RollForwardRegion(
        region_id="rfr-table-15-iqr",
        section_name="Section 7: Benchmarking Results",
        target_document_id="doc-tmpl-decree20",
        target_element_ids=["table-15-hash-d7c319bd"],
        classification=RegionClassification.REPEATABLE,
        current_sources=[
            SourceBinding(
                source_doc_id="doc-bm-fy2024",
                source_doc_name="HMV-25-Draft BM FY24-W1203.xlsb",
                source_type=SourceType.XLSX,
                sheet_name="Final Set",
                cell_range="A5:G21",
                match_basis=["interquartile_range_margins"],
                status=SourceBindingStatus.VERIFIED,
                reason="Comparable companies 3-year weighted average NCP margins",
            )
        ],
        structural_delta=StructuralDelta(
            template_rows=7,
            target_rows=16,
            insert_count=6,
            delete_count=0,
            row_template_anchor="table:15:d7c319bd_row:1",
            observation_source="benchmarking_study_iqr_margins",
        ),
        validation_rules=[
            ValidationRule(
                rule_type=ValidationRuleType.ROW_COUNT_MATCH,
                severity=ValidationSeverity.BLOCKER,
                parameters={"expected_rows": 16},
                description="Verify 16 rows corresponding to peer companies + quartiles",
            )
        ],
        mutation_strategy="CLONE_ROW_AND_POPULATE",
    )

    assert region.structural_delta.insert_count == 6
    assert region.execution_gate == ExecutionGate.READY


def test_real_figure_1_diagram_replacement():
    """Verify Figure 1 (Ownership Chart) regeneration binding."""
    fig = FigureBinding(
        target_element_id="fig-01-ownership",
        target_doc_id="doc-tmpl-decree20",
        historical_reference=HistoricalReference(
            doc_id="doc-hist-fy2023",
            element_id="image1.png",
            ground_truth_status=GroundTruthStatus.STRONGLY_SUPPORTED,
        ),
        current_source=SourceBinding(
            source_doc_id="doc-farpt-fy2024",
            source_doc_name="HMV-FA&RPT FY2024.xlsx",
            sheet_name="I. Related parties",
            cell_address="B14",
            match_basis=["ultimate_parent_shareholding"],
            status=SourceBindingStatus.VERIFIED,
            reason="Shareholding buyout (100% Martin Magnusson & CO. AB)",
        ),
        media_id="docx-rel:rId10",
        source_ref="word/media/image1.png",
        strategy=RegionClassification.REGENERATE,
        validation_rules=[
            ValidationRule(
                rule_type=ValidationRuleType.IMAGE_PRESENT,
                severity=ValidationSeverity.BLOCKER,
                description="Ensure replacement diagram asset is valid PNG",
            )
        ],
    )

    assert fig.strategy == RegionClassification.REGENERATE
    assert fig.media_id == "docx-rel:rId10"


def test_execution_gate_blocked_on_manual_review_or_unknown():
    """UNKNOWN and MANUAL_REVIEW regions must remain BLOCKED."""
    r_unknown = RollForwardRegion(
        region_id="rfr-unknown",
        section_name="Section X: Custom Addendum",
        target_document_id="doc-tmpl-decree20",
        classification=RegionClassification.UNKNOWN,
    )
    assert r_unknown.execution_gate == ExecutionGate.BLOCKED
    assert r_unknown.requires_manual_review() is True

    r_review = RollForwardRegion(
        region_id="rfr-review",
        section_name="Section 4: FAR Analysis",
        target_document_id="doc-tmpl-decree20",
        classification=RegionClassification.MANUAL_REVIEW,
    )
    assert r_review.execution_gate == ExecutionGate.BLOCKED
    assert r_review.requires_manual_review() is True


def test_execution_gate_blocked_on_stale_or_ambiguous_source():
    """Regions with non-VERIFIED source bindings must remain BLOCKED."""
    for bad_status in (
        SourceBindingStatus.UNVERIFIED,
        SourceBindingStatus.AMBIGUOUS,
        SourceBindingStatus.STALE,
        SourceBindingStatus.MISSING,
    ):
        region = RollForwardRegion(
            region_id=f"rfr-{bad_status.value.lower()}",
            section_name="Section 3: Transactions",
            target_document_id="doc-tmpl-decree20",
            classification=RegionClassification.UPDATE,
            current_sources=[
                SourceBinding(
                    source_doc_id="doc-test",
                    source_doc_name="test.xlsx",
                    sheet_name="RPTs",
                    cell_address="C5",
                    status=bad_status,
                )
            ],
        )
        assert region.execution_gate == ExecutionGate.BLOCKED
        if bad_status in (SourceBindingStatus.AMBIGUOUS, SourceBindingStatus.MISSING, SourceBindingStatus.STALE):
            assert region.requires_manual_review() is True


def test_state_machine_legal_lifecycle():
    """Verify happy-path transition: DISCOVERED -> PLANNED -> APPROVED -> EXECUTING -> VALIDATED -> COMPLETED."""
    manifest = RollForwardManifest(
        session_id="session-legal-01",
        template_document_id="doc-tmpl",
        regions=[
            RollForwardRegion(
                region_id="rfr-clean",
                section_name="Section 1",
                target_document_id="doc-tmpl",
                classification=RegionClassification.UPDATE,
                current_sources=[
                    SourceBinding(
                        source_doc_id="doc-src",
                        source_doc_name="data.xlsx",
                        status=SourceBindingStatus.VERIFIED,
                    )
                ],
            )
        ],
    )
    assert manifest.status == ManifestStatus.DISCOVERED

    # 1. DISCOVERED -> PLANNED
    RollForwardStateMachine.transition(manifest, ManifestStatus.PLANNED, actor="agent")
    assert manifest.status == ManifestStatus.PLANNED

    # 2. PLANNED -> APPROVED (by user)
    RollForwardStateMachine.approve(manifest, user_name="tax_senior_manager@kpmg.com")
    assert manifest.status == ManifestStatus.APPROVED
    assert manifest.approved_by == "tax_senior_manager@kpmg.com"
    assert manifest.approved_manifest_version == 1

    # 3. APPROVED -> EXECUTING
    RollForwardStateMachine.start_execution(manifest, actor="system")
    assert manifest.status == ManifestStatus.EXECUTING

    # 4. EXECUTING -> VALIDATED
    RollForwardStateMachine.mark_validated(manifest)
    assert manifest.status == ManifestStatus.VALIDATED

    # 5. VALIDATED -> COMPLETED
    RollForwardStateMachine.mark_completed(manifest, actor="user")
    assert manifest.status == ManifestStatus.COMPLETED

    assert len(manifest.history) == 5


def test_agent_cannot_approve_manifest():
    """Agent or System actors attempting to approve a manifest MUST be rejected."""
    manifest = RollForwardManifest(
        session_id="session-agent-approve",
        template_document_id="doc-tmpl",
        status=ManifestStatus.PLANNED,
    )

    with pytest.raises(UnauthorizedApprovalError, match="Only explicit user action can approve"):
        RollForwardStateMachine.transition(
            manifest=manifest,
            target_status=ManifestStatus.APPROVED,
            actor="agent",
            reason="Agent attempted auto-approval",
        )

    with pytest.raises(UnauthorizedApprovalError, match="Only explicit user action can approve"):
        RollForwardStateMachine.transition(
            manifest=manifest,
            target_status=ManifestStatus.APPROVED,
            actor="system",
            reason="System attempted auto-approval",
        )


def test_review_gating_enforces_review_required():
    """If manifest has unresolved manual reviews, direct PLANNED -> APPROVED is blocked."""
    manifest = RollForwardManifest(
        session_id="session-review-gate",
        template_document_id="doc-tmpl",
        status=ManifestStatus.PLANNED,
        regions=[
            RollForwardRegion(
                region_id="rfr-manual",
                section_name="Section 4: FAR",
                target_document_id="doc-tmpl",
                classification=RegionClassification.MANUAL_REVIEW,
            )
        ],
    )
    assert manifest.has_unresolved_reviews() is True

    # User cannot jump directly from PLANNED to APPROVED if reviews are required
    with pytest.raises(IllegalTransitionError, match="Must transition to REVIEW_REQUIRED before approval"):
        RollForwardStateMachine.approve(manifest, user_name="auditor@firm.com")

    # Correct path: PLANNED -> REVIEW_REQUIRED -> APPROVED
    RollForwardStateMachine.transition(manifest, ManifestStatus.REVIEW_REQUIRED, actor="agent")
    assert manifest.status == ManifestStatus.REVIEW_REQUIRED

    # Now user reviews and explicitly approves
    RollForwardStateMachine.approve(manifest, user_name="auditor@firm.com")
    assert manifest.status == ManifestStatus.APPROVED


def test_approval_invalidation_after_manifest_modification():
    """Modifying a manifest after approval invalidates that approval and increments version."""
    manifest = RollForwardManifest(
        session_id="session-invalidation",
        template_document_id="doc-tmpl",
        status=ManifestStatus.PLANNED,
        regions=[
            RollForwardRegion(
                region_id="rfr-1",
                section_name="Section 1",
                target_document_id="doc-tmpl",
                classification=RegionClassification.UPDATE,
                current_sources=[
                    SourceBinding(
                        source_doc_id="doc-src",
                        source_doc_name="data.xlsx",
                        status=SourceBindingStatus.VERIFIED,
                    )
                ],
            )
        ],
    )

    RollForwardStateMachine.approve(manifest, user_name="partner@kpmg.com")
    assert manifest.status == ManifestStatus.APPROVED
    assert manifest.manifest_version == 1
    assert manifest.approved_manifest_version == 1

    # Now manifest is modified (e.g. Agent updates a binding)
    manifest.mark_modified(actor="agent")

    assert manifest.manifest_version == 2
    assert manifest.parent_version == 1
    assert manifest.status == ManifestStatus.PLANNED
    assert manifest.approved_by is None
    assert manifest.approved_at is None
    assert manifest.approved_manifest_version is None
    assert manifest.is_execution_ready() is False

    # Attempting to start execution on modified manifest in PLANNED status must fail with IllegalTransitionError
    with pytest.raises(IllegalTransitionError, match="Illegal state transition from PLANNED to EXECUTING"):
        RollForwardStateMachine.start_execution(manifest)

    # If status were forcefully set to APPROVED without user approval of version 2, is_execution_ready is False
    manifest.status = ManifestStatus.APPROVED
    assert manifest.is_execution_ready() is False
    with pytest.raises(ApprovalInvalidationError, match="is not execution-ready"):
        RollForwardStateMachine.start_execution(manifest)


def test_illegal_transitions_rejected():
    """Verify rejection of various illegal state transitions."""
    manifest = RollForwardManifest(
        session_id="session-illegal-test",
        template_document_id="doc-tmpl",
        status=ManifestStatus.DISCOVERED,
    )

    # 1. DISCOVERED -> EXECUTING (Illegal jump)
    with pytest.raises(IllegalTransitionError, match="Illegal state transition from DISCOVERED to EXECUTING"):
        RollForwardStateMachine.transition(manifest, ManifestStatus.EXECUTING, actor="system")

    # 2. DISCOVERED -> APPROVED (Illegal jump)
    with pytest.raises(IllegalTransitionError, match="Illegal state transition from DISCOVERED to APPROVED"):
        RollForwardStateMachine.transition(manifest, ManifestStatus.APPROVED, actor="user")

    # Transition to EXECUTING via legal flow
    RollForwardStateMachine.transition(manifest, ManifestStatus.PLANNED, actor="agent")
    RollForwardStateMachine.approve(manifest, user_name="reviewer")
    RollForwardStateMachine.start_execution(manifest)
    assert manifest.status == ManifestStatus.EXECUTING

    # 3. EXECUTING -> APPROVED (Illegal back-transition)
    with pytest.raises(IllegalTransitionError, match="Illegal state transition from EXECUTING to APPROVED"):
        RollForwardStateMachine.transition(manifest, ManifestStatus.APPROVED, actor="user")

    # 4. COMPLETED -> EXECUTING (Illegal transition from terminal state)
    RollForwardStateMachine.mark_validated(manifest)
    RollForwardStateMachine.mark_completed(manifest)
    assert manifest.status == ManifestStatus.COMPLETED

    with pytest.raises(IllegalTransitionError, match="Illegal state transition from COMPLETED"):
        RollForwardStateMachine.start_execution(manifest)


def test_failed_execution_recovery_flow():
    """Verify execution failure handling and transition back to PLANNED."""
    manifest = RollForwardManifest(
        session_id="session-failure-recovery",
        template_document_id="doc-tmpl",
        status=ManifestStatus.PLANNED,
        regions=[
            RollForwardRegion(
                region_id="rfr-1",
                section_name="Section 1",
                target_document_id="doc-tmpl",
                classification=RegionClassification.UPDATE,
                current_sources=[
                    SourceBinding(
                        source_doc_id="doc-src",
                        source_doc_name="data.xlsx",
                        status=SourceBindingStatus.VERIFIED,
                    )
                ],
            )
        ],
    )

    RollForwardStateMachine.approve(manifest, user_name="lead@firm.com")
    RollForwardStateMachine.start_execution(manifest)
    assert manifest.status == ManifestStatus.EXECUTING

    # Execution fails
    RollForwardStateMachine.mark_failed(manifest, error_message="OpenXML schema validation error: corrupted table row")
    assert manifest.status == ManifestStatus.FAILED
    assert manifest.history[-1].reason == "OpenXML schema validation error: corrupted table row"

    # Recovery: FAILED -> PLANNED
    RollForwardStateMachine.transition(manifest, ManifestStatus.PLANNED, actor="agent", reason="Re-planning after failure")
    assert manifest.status == ManifestStatus.PLANNED

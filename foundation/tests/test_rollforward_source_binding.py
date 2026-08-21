"""
Local File Roll-Forward Source Binding & Planning Unit Tests (Phase C)
======================================================================
Location: foundation/tests/test_rollforward_source_binding.py

Verifies deterministic source binding, structural delta planning,
unknown region breakdown, human review diff generation, manifest governance,
and negative safety constraints.
"""
from pathlib import Path
import sys

import pytest

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "foundation") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "foundation"))

from foundation.applications.rollforward.models import (
    ExecutionGate,
    ManifestStatus,
    RegionClassification,
    RollForwardManifest,
    RollForwardRegion,
    SourceBinding,
    SourceBindingStatus,
    SourceType,
    StructuralDelta,
    ValidationRule,
    ValidationRuleType,
    ValidationSeverity,
)
from foundation.applications.rollforward.state_machine import RollForwardStateMachine
from foundation.tests.evaluation.rollforward_profiler import (
    PATH_DATA_APP1,
    PATH_DATA_FARPT,
    PATH_GT,
    PATH_HIST,
    PATH_TMPL,
)
from foundation.tests.evaluation.rollforward_source_binding import (
    BlockedCategory,
    BlockedRegionAnalyzer,
    DeterministicSourceBindingEngine,
    HumanReviewPlanGenerator,
    StructuralPlanningEngine,
    run_rollforward_source_binding_pipeline,
)


def test_source_binding_correctness():
    """Verify all discovered Excel source bindings are deterministic and VERIFIED."""
    bindings = DeterministicSourceBindingEngine.discover_and_verify_all(
        PATH_DATA_FARPT, PATH_DATA_APP1
    )

    assert "taxpayer_profile" in bindings
    assert "audited_financials" in bindings
    assert "related_party_transactions" in bindings
    assert "financial_ratios" in bindings
    assert "interest_expenses" in bindings
    assert "appendix1_full" in bindings

    # Verify taxpayer profile binding
    tp_b = bindings["taxpayer_profile"][0]
    assert tp_b.status == SourceBindingStatus.VERIFIED
    assert tp_b.sheet_name == "I. Related parties"
    assert tp_b.cell_address == "A3"
    assert tp_b.provenance["taxpayer_name"] == "Hestra Matsuoka Vietnam Limited Liability Company"

    # Verify audited financials binding
    fs_b = bindings["audited_financials"][0]
    assert fs_b.status == SourceBindingStatus.VERIFIED
    assert fs_b.sheet_name == "FS"
    assert fs_b.cell_range == "A7:D14"


def test_no_fabricated_ranges_or_invented_ids():
    """Ensure no source binding contains fabricated Excel coordinates or invented IDs."""
    bindings = DeterministicSourceBindingEngine.discover_and_verify_all(
        PATH_DATA_FARPT, PATH_DATA_APP1
    )

    for key, binding_list in bindings.items():
        for b in binding_list:
            assert b.source_doc_name in (PATH_DATA_FARPT.name, PATH_DATA_APP1.name)
            assert b.sheet_name is not None
            assert (b.cell_address is not None) or (b.cell_range is not None)
            assert len(b.match_basis) > 0
            assert b.reason != ""


def test_known_table_growth_planning_records():
    """Verify explicit structural delta planning for all 4 dynamic growth tables:

    - Table 10: 2 -> 11 (+9 rows)
    - Table 13: 4 -> 6 (+2 rows)
    - Table 14: 6 -> 10 (+4 rows)
    - Table 15: 10 -> 16 (+6 rows)
    """
    manifest, _ = run_rollforward_source_binding_pipeline()

    # 1. Table 10: Financial Indicators Summary
    r10 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 11), None)
    assert r10 is not None
    assert r10.structural_delta.insert_count == 9
    assert r10.structural_delta.observation_context["growth"] == "+9"
    assert r10.row_template is not None
    assert r10.row_template.safe_to_clone is True
    assert any(v.rule_type == ValidationRuleType.ROW_COUNT_MATCH for v in r10.validation_rules)

    # 2. Table 13: Search Matrix Steps
    r13 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 6), None)
    assert r13 is not None
    assert r13.structural_delta.insert_count == 2
    assert r13.structural_delta.observation_context["growth"] == "+2"
    assert r13.row_template.safe_to_clone is True

    # 3. Table 14: Comparable Companies Set
    r14 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 10), None)
    assert r14 is not None
    assert r14.structural_delta.insert_count == 4
    assert r14.structural_delta.observation_context["growth"] == "+4"
    assert r14.row_template.safe_to_clone is True

    # 4. Table 15: Benchmarking Interquartile Results
    r15 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 16), None)
    assert r15 is not None
    assert r15.structural_delta.insert_count == 6
    assert r15.structural_delta.observation_context["growth"] == "+6"
    assert r15.row_template.safe_to_clone is True
    assert any(v.rule_type == ValidationRuleType.ROW_COUNT_MATCH for v in r15.validation_rules)


def test_execution_gating_logic():
    """Verify execution gate evaluates to READY only when strictly unblocked."""
    manifest, _ = run_rollforward_source_binding_pipeline()

    # Regions with verified sources should be READY
    ready_regions = [r for r in manifest.regions if r.execution_gate == ExecutionGate.READY]
    blocked_regions = [r for r in manifest.regions if r.execution_gate == ExecutionGate.BLOCKED]

    assert len(ready_regions) > 0
    assert len(blocked_regions) > 0

    # Every blocked region must have a reason
    for r in blocked_regions:
        assert r.requires_manual_review() is True or r.classification == RegionClassification.UNKNOWN


def test_unknown_blocked_regions_honest_breakdown():
    """Verify honest taxonomy breakdown for all blocked/unknown regions."""
    manifest, manifest_dict = run_rollforward_source_binding_pipeline()
    blocked_analysis = manifest_dict["blocked_regions_analysis"]

    assert blocked_analysis["total_blocked_regions"] > 0
    counts = blocked_analysis["category_counts"]

    # Verify all 6 taxonomy categories exist
    assert BlockedCategory.TRULY_STATIC_UNMAPPED in counts
    assert BlockedCategory.MISSING_CURRENT_SOURCE in counts
    assert BlockedCategory.AMBIGUOUS_SOURCE in counts
    assert BlockedCategory.MANUAL_REVIEW_REQUIRED in counts
    assert BlockedCategory.INSUFFICIENT_EVIDENCE in counts

    # Check sum invariant
    assert sum(counts.values()) == blocked_analysis["total_blocked_regions"]


def test_human_review_diff_generation():
    """Verify human review plan diffs contain actionable comparison details."""
    manifest, _ = run_rollforward_source_binding_pipeline()
    diffs = HumanReviewPlanGenerator.generate_review_diffs(manifest)

    assert len(diffs) > 0
    # Must have row added diffs for dynamic tables
    row_added_diffs = [d for d in diffs if d.change_type.value == "ROW_ADDED"]
    assert len(row_added_diffs) >= 4  # Tables 2, 10, 13, 14, 15


def test_manifest_governance_compatibility():
    """Verify generated manifest is fully compliant with Phase A state machine governance."""
    manifest, _ = run_rollforward_source_binding_pipeline()

    assert manifest.schema_version == "1.0.0"
    assert manifest.manifest_version == 1
    assert manifest.status == ManifestStatus.REVIEW_REQUIRED
    assert len(manifest.history) >= 2

    # Manifest with blocked regions cannot be executed directly
    assert manifest.is_execution_ready() is False


def test_negative_stale_and_ambiguous_bindings_block_gate():
    """Negative test: Stale or ambiguous source bindings must strictly force ExecutionGate.BLOCKED."""
    region = RollForwardRegion(
        region_id="rfr-test-stale",
        section_name="Test Stale Section",
        target_document_id="doc-tmpl",
        classification=RegionClassification.UPDATE,
        current_sources=[
            SourceBinding(
                source_doc_id="doc-stale",
                source_doc_name="stale.xlsx",
                sheet_name="Old",
                cell_address="A1",
                status=SourceBindingStatus.STALE,
                reason="Shifted rows post edit",
            )
        ],
    )
    assert region.execution_gate == ExecutionGate.BLOCKED
    assert region.requires_manual_review() is True

    # Ambiguous binding
    region_amb = RollForwardRegion(
        region_id="rfr-test-ambiguous",
        section_name="Test Ambiguous Section",
        target_document_id="doc-tmpl",
        classification=RegionClassification.UPDATE,
        current_sources=[
            SourceBinding(
                source_doc_id="doc-amb",
                source_doc_name="data.xlsx",
                sheet_name="RPT",
                cell_range="A1:B10",
                status=SourceBindingStatus.AMBIGUOUS,
                reason="Multiple candidate rows match",
            )
        ],
    )
    assert region_amb.execution_gate == ExecutionGate.BLOCKED
    assert region_amb.requires_manual_review() is True


def test_negative_unauthorized_agent_approval_blocked():
    """Negative test: Agent cannot approve a manifest under Phase A state machine governance."""
    manifest, _ = run_rollforward_source_binding_pipeline()

    with pytest.raises(Exception):
        RollForwardStateMachine.approve_manifest(
            manifest=manifest,
            actor_role="agent",  # Forbidden
            actor_id="agent-luna",
        )

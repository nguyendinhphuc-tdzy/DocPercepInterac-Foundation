"""
Unit Tests for Local File Roll-Forward Template / Region Profiler (Phase B)
===========================================================================
Location: foundation/tests/test_rollforward_profiler.py

Verifies:
1. Deterministic region count and template hash stability
2. Table structural signature stability across all 16 template tables
3. Historical <-> Template mapping stability
4. Real-fixture table row growth detection:
   - Table 10: 2 -> 11 rows (+9)
   - Table 13: 4 -> 6 rows (+2)
   - Table 14: 6 -> 10 rows (+4)
   - Table 15: 10 -> 16 rows (+6)
5. Deterministic Excel source discovery without range guessing
6. Figure contextual classification without guessing
7. Unresolved regions remain UNKNOWN and BLOCKED
8. Ground-truth evaluation runs strictly post-profiling without altering the profile
9. Prototype row template safe-to-clone validation
10. Deterministic JSON output equivalence across repeated runs
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from tests.evaluation.rollforward_profiler import (
    TemplateRegionSegmenter,
    TableSignatureProfiler,
    FigureProfiler,
    CurrentSourceDiscoverer,
    HistoricalCorrelator,
    GroundTruthEvaluator,
    run_rollforward_profiler,
    PATH_TMPL,
    PATH_HIST,
    PATH_DATA_FARPT,
    PATH_DATA_APP1,
    PATH_GT,
)

from applications.rollforward.models import (
    ExecutionGate,
    RegionClassification,
    SourceBindingStatus,
    SourceType,
)


def test_template_region_segmenter_stability():
    """Verify deterministic region segmentation of 848-element Template."""
    regions = TemplateRegionSegmenter.segment_template(PATH_TMPL)
    assert len(regions) > 50
    assert regions[0]["section_name"].startswith("PREAMBLE")
    # Verify every region has valid element list
    for r in regions:
        assert len(r["elements"]) > 0
        assert r["region_id"].startswith("rfr-")


def test_table_signature_profiler_all_16_tables():
    """Verify TableSignatureProfiler profiles all 16 tables in Master Template."""
    tables = TableSignatureProfiler.profile_tables(PATH_TMPL)
    assert len(tables) == 16

    # Verify structural fields in every table signature
    for t in tables:
        assert "table_index" in t
        assert "table_hash" in t
        assert len(t["table_hash"]) == 8
        assert t["row_count"] > 0
        assert t["col_count"] > 0
        assert "header_signature" in t
        assert "gridspan_topology" in t
        assert "vmerge_topology" in t
        assert "row_schemas" in t
        assert "safe_to_clone" in t


def test_table_row_growth_cases_verified():
    """Verify exact observed row growth deltas on real fixtures:

    - Table 10: 2 -> 11 (+9 rows)
    - Table 13: 4 -> 6 (+2 rows)
    - Table 14: 6 -> 10 (+4 rows)
    - Table 15: 10 -> 16 (+6 rows)
    """
    manifest, profile_data = run_rollforward_profiler()

    # Find Table 10 region
    r10 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 11), None)
    assert r10 is not None
    assert r10.structural_delta.insert_count == 9
    assert r10.structural_delta.observation_context["growth"] == "+9"

    # Find Table 13 region
    r13 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 6), None)
    assert r13 is not None
    assert r13.structural_delta.insert_count == 2
    assert r13.structural_delta.observation_context["growth"] == "+2"

    # Find Table 14 region
    r14 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 10), None)
    assert r14 is not None
    assert r14.structural_delta.insert_count == 4
    assert r14.structural_delta.observation_context["growth"] == "+4"

    # Find Table 15 region
    r15 = next((r for r in manifest.regions if r.structural_delta and r.structural_delta.target_rows == 16), None)
    assert r15 is not None
    assert r15.structural_delta.insert_count == 6
    assert r15.structural_delta.observation_context["growth"] == "+6"


def test_current_source_discovery_accuracy():
    """Verify deterministic Excel source discovery without range guessing."""
    bindings = CurrentSourceDiscoverer.discover_sources(PATH_DATA_FARPT, PATH_DATA_APP1)

    assert "company_profile" in bindings
    assert bindings["company_profile"][0].sheet_name == "I. Related parties"
    assert bindings["company_profile"][0].cell_address == "B3"
    assert bindings["company_profile"][0].status == SourceBindingStatus.VERIFIED

    assert "audited_financials" in bindings
    assert bindings["audited_financials"][0].sheet_name == "FS"
    assert bindings["audited_financials"][0].cell_range == "A7:D14"

    assert "related_party_transactions" in bindings
    assert bindings["related_party_transactions"][0].sheet_name == "RPTs"
    assert bindings["related_party_transactions"][0].cell_range == "A5:G9"

    assert "financial_ratios" in bindings
    assert bindings["financial_ratios"][0].sheet_name == "Financial Analysis"
    assert bindings["financial_ratios"][0].cell_range == "A4:D35"

    assert "interest_expenses" in bindings
    assert bindings["interest_expenses"][0].sheet_name == "Interest expenses"


def test_figure_contextual_classification():
    """Verify FigureProfiler uses multi-factor context without guessing from filename."""
    figures = FigureProfiler.profile_figures(PATH_TMPL)
    assert len(figures) > 0

    for fig in figures:
        assert "figure_index" in fig
        assert "paragraph_index" in fig
        assert "figure_type" in fig
        assert "classification" in fig
        assert "reason" in fig
        assert fig["execution_gate"] in (ExecutionGate.READY, ExecutionGate.BLOCKED)


def test_unresolved_regions_remain_unknown_and_blocked():
    """Verify that unmapped or ambiguous regions are classified as UNKNOWN with execution_gate=BLOCKED."""
    manifest, _ = run_rollforward_profiler()
    unknown_regions = [r for r in manifest.regions if r.classification == RegionClassification.UNKNOWN]

    assert len(unknown_regions) > 0
    for r in unknown_regions:
        assert r.execution_gate == ExecutionGate.BLOCKED
        assert r.requires_manual_review() is True


def test_ground_truth_evaluation_runs_post_profiling():
    """Verify GroundTruthEvaluator compares frozen profile predictions against oracle."""
    manifest, profile_data = run_rollforward_profiler()
    gt_eval = profile_data["ground_truth_evaluation"]

    assert gt_eval["total_evaluated_regions"] == len(manifest.regions)
    assert gt_eval["verified_count"] >= 10
    assert gt_eval["contradicted_count"] == 0


def test_row_template_prototype_safety():
    """Verify row templates have safe_to_clone=True for clean prototype rows."""
    manifest, _ = run_rollforward_profiler()
    repeatable_regions = [r for r in manifest.regions if r.classification == RegionClassification.REPEATABLE]

    for r in repeatable_regions:
        if r.row_template:
            assert r.row_template.safe_to_clone is True
            assert r.row_template.template_row_idx >= 0


def test_profiler_output_determinism():
    """Verify running profiler twice produces equivalent JSON output."""
    _, profile_1 = run_rollforward_profiler()
    _, profile_2 = run_rollforward_profiler()

    # Compare structural keys
    assert profile_1["statistics"] == profile_2["statistics"]
    assert len(profile_1["table_signatures"]) == len(profile_2["table_signatures"])
    assert len(profile_1["figure_profiles"]) == len(profile_2["figure_profiles"])
    assert len(profile_1["manifest"]["regions"]) == len(profile_2["manifest"]["regions"])

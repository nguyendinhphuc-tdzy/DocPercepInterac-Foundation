from __future__ import annotations

import json
from pathlib import Path

from foundation.evaluation.golden import DummyGoldenAdapter, GoldenHarness, load_manifest


HERE = Path(__file__).resolve().parent


def test_synthetic_manifest_runs_end_to_end(tmp_path):
    manifest = load_manifest(HERE / "corpus_manifest.yaml")
    report_path = tmp_path / "golden-report.json"
    report = GoldenHarness(DummyGoldenAdapter()).run(manifest, report_path)
    assert report.total_cases == 1
    assert report.passed_cases == 1
    assert report.failed_cases == 0
    assert report.qualification_claimed is False
    assert json.loads(report_path.read_text(encoding="utf-8"))["overall_result"] == "PASS"


def test_comparator_reports_observation_drift():
    manifest = load_manifest(HERE / "corpus_manifest.yaml")
    adapter = DummyGoldenAdapter(force_capability="UNSUPPORTED")
    report = GoldenHarness(adapter).run(manifest)
    assert report.failed_cases == 1
    assert "capability" in " ".join(report.results[0].differences).lower()

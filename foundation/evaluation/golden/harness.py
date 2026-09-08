"""Deterministic engine-neutral Golden Corpus harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import yaml

from foundation.domain import CapabilityStatus

from .models import GoldenCase, GoldenManifest, GoldenObservation, GoldenReport, GoldenResult


class GoldenAdapter(Protocol):
    def observe(self, case: GoldenCase) -> GoldenObservation: ...


class DummyGoldenAdapter:
    """Synthetic harness adapter. It makes no engine qualification claim."""

    def __init__(self, force_capability: CapabilityStatus | str | None = None):
        self.force_capability = CapabilityStatus(force_capability) if force_capability else None

    def observe(self, case: GoldenCase) -> GoldenObservation:
        return GoldenObservation(
            case_id=case.case_id,
            adapter_id="b0-dummy-adapter",
            adapter_version="0.1.0",
            observed_capability=self.force_capability or case.expected_capability,
            preservation_observations=list(case.expected_preservation),
            error_code=case.expected_failure,
        )


def load_manifest(path: Path) -> GoldenManifest:
    return GoldenManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class GoldenHarness:
    def __init__(self, adapter: GoldenAdapter):
        self.adapter = adapter

    def run(self, manifest: GoldenManifest, report_path: Path | None = None) -> GoldenReport:
        results = tuple(self._compare(case, self.adapter.observe(case)) for case in manifest.cases)
        passed = sum(item.passed for item in results)
        report = GoldenReport(
            schema_version="0.1.0",
            manifest_id=manifest.manifest_id,
            qualification_claimed=False,
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=len(results) - passed,
            overall_result="PASS" if passed == len(results) else "FAIL",
            results=list(results),
        )
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return report

    @staticmethod
    def _compare(case: GoldenCase, observation: GoldenObservation) -> GoldenResult:
        differences: list[str] = []
        if observation.case_id != case.case_id:
            differences.append("case identity mismatch")
        if observation.observed_capability is not case.expected_capability:
            differences.append("capability mismatch")
        if observation.error_code is not case.expected_failure:
            differences.append("failure outcome mismatch")
        missing = [item for item in case.expected_preservation if item not in observation.preservation_observations]
        if missing:
            differences.append("missing preservation observations: " + ", ".join(missing))
        return GoldenResult(case_id=case.case_id, passed=not differences, differences=differences, observation=observation)

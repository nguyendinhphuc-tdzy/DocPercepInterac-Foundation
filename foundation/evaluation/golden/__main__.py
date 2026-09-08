"""Run the B0 dummy Golden Corpus adapter against a manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from .harness import DummyGoldenAdapter, GoldenHarness, load_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = GoldenHarness(DummyGoldenAdapter()).run(load_manifest(args.manifest), args.report)
    return 0 if report.overall_result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

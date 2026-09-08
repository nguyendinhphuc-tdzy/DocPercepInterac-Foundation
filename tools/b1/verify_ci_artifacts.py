"""Operational artifact retention verification for CI; no domain authority."""

import argparse
import json
from pathlib import Path
import sys

EXPECTED_FILES = (
    "b1-ci-reports/preflight.json",
    "b1-ci-reports/docling-qualification.json",
    "contract-validation-report.json",
)

MINIMUM_SEMANTIC_KEYS = {
    "b1-ci-reports/preflight.json": (
        "evaluation_version",
        "cases",
    ),
    "b1-ci-reports/docling-qualification.json": (
        "qualification_status",
        "engine",
        "engine_version",
        "cases",
        "reproducible_payload_sha256",
    ),
    "contract-validation-report.json": (
        "fixtures_evaluated",
    ),
}


def verify_artifacts(root=Path("."), require_semantic_keys: bool = False):
    root = Path(root) if root is not None else Path(".")
    verified = []
    for name in EXPECTED_FILES:
        path = root / name
        if not path.exists():
            raise ValueError(f"Required CI artifact '{name}' does not exist at {path}")
        if not path.is_file():
            raise ValueError(f"Required CI artifact '{name}' is not a regular file")
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"Required CI artifact '{name}' is empty")
        try:
            data = json.loads(content)
        except Exception as exc:
            raise ValueError(f"Required CI artifact '{name}' malformed: {exc}")
        if not isinstance(data, dict):
            raise ValueError(f"Required CI artifact '{name}' must be a JSON object")

        if require_semantic_keys and name in MINIMUM_SEMANTIC_KEYS:
            for key in MINIMUM_SEMANTIC_KEYS[name]:
                if key not in data:
                    raise ValueError(
                        f"Required CI artifact '{name}' is missing expected semantic key '{key}'"
                    )

        verified.append(name)
    return verified


def main():
    parser = argparse.ArgumentParser(
        description="Verify that required CI evidence artifacts exist, are non-empty, and parse."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Root workspace path where artifacts are located.",
    )
    parser.add_argument(
        "--require-semantic-keys",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also verify minimum semantic keys in addition to existence and valid JSON.",
    )
    args = parser.parse_args()
    try:
        verified = verify_artifacts(
            args.root, require_semantic_keys=args.require_semantic_keys
        )
        for item in verified:
            print(f"VERIFIED ARTIFACT: {item}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

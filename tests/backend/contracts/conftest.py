from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES_DIR = REPOSITORY_ROOT / "docs" / "contracts" / "examples"
OPENAPI_PATH = REPOSITORY_ROOT / "docs" / "contracts" / "foundation.openapi.yaml"
FIXTURE_PATHS = tuple(sorted(EXAMPLES_DIR.glob("[0-9][0-9]-*.yaml")))


@pytest.fixture(scope="session")
def contract_fixtures() -> tuple[tuple[Path, dict[str, object]], ...]:
    return tuple(
        (path, yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in FIXTURE_PATHS
    )


@pytest.fixture(scope="session")
def openapi_document() -> dict[str, object]:
    return yaml.safe_load(OPENAPI_PATH.read_text(encoding="utf-8"))

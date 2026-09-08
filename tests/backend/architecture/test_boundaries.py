from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CORE = [ROOT / "foundation/domain", ROOT / "foundation/governance", ROOT / "foundation/audit", ROOT / "foundation/ports"]
FORBIDDEN = {
    "foundation.output.writeback",
    "foundation.applications.agent.action_executor",
    "foundation.applications.rollforward.structural_writeback",
    "foundation.api",
    "api",
    "frontend",
}


def test_v2_core_does_not_import_legacy_mutation_or_delivery_layers():
    violations = []
    for directory in CORE:
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [item.name for item in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if any(name == item or name.startswith(item + ".") for item in FORBIDDEN):
                        violations.append((path.relative_to(ROOT).as_posix(), name))
    assert violations == []

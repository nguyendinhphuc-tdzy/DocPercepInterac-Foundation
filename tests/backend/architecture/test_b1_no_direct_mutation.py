"""B1 is read-only. Legacy modules remain outside this enforced boundary."""

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
GOVERNED = ("foundation/adapters", "foundation/services", "foundation/ports",
            "foundation/domain", "foundation/governance", "foundation/audit",
            "foundation/evaluation", "tools/b1")
FORBIDDEN = ("foundation.output", "foundation.applications", "foundation.api",
             "foundation.perception", "output.writeback", "api.routes")
WRITE_SYMBOLS = {"WritebackEngine", "apply_single_patch", "patch_element"}


def violations(source, module):
    findings = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = ".".join(module.split(".")[:-node.level] + ([base] if base else []))
            names = [base, *(base + "." + alias.name for alias in node.names)]
        elif isinstance(node, ast.Call):
            function = node.func
            if ((isinstance(function, ast.Name) and function.id == "__import__") or
                    (isinstance(function, ast.Attribute) and function.attr == "import_module")):
                if node.args and isinstance(node.args[0], ast.Constant):
                    names = [str(node.args[0].value)]
                else:
                    findings.append("uninspectable dynamic import")
        if any(name == prefix or name.startswith(prefix + ".") for name in names for prefix in FORBIDDEN):
            findings.append("legacy dependency")
        if ((isinstance(node, ast.Attribute) and node.attr in WRITE_SYMBOLS) or
                (isinstance(node, ast.Name) and node.id in WRITE_SYMBOLS) or
                (isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in WRITE_SYMBOLS)):
            findings.append("direct write symbol")
    return findings


@pytest.mark.parametrize("source", [
    "from foundation.output.writeback import WritebackEngine as W",
    "import foundation.output.writeback as w",
    "from ..output import writeback",
    "engine.apply_single_patch(value)",
    "getattr(engine, 'apply_single_patch')(value)",
    "importlib.import_module('foundation.output.writeback')",
    "__import__('foundation.output.writeback')",
])
def test_guard_detects_legacy_imports_and_calls(source):
    assert violations(source, "foundation.adapters.example")


def test_new_b1_and_governed_modules_cannot_reach_legacy_direct_write():
    found = []
    for directory in GOVERNED:
        for path in (ROOT / directory).rglob("*.py"):
            module = path.relative_to(ROOT).with_suffix("").as_posix().replace("/", ".")
            found.extend((path.relative_to(ROOT).as_posix(), item)
                         for item in violations(path.read_text(encoding="utf-8"), module))
    assert found == []

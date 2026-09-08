"""Semantic-to-machine drift audit, separate from fixture machine validation.

Markdown parsing is confined here. No fixture validator imports this module.
"""
from pathlib import Path
import re
import unittest

from tools.contracts.validate_contract_fixtures import CONTRACTS, MachineContract, load_openapi_contract


class ProjectionDriftTests(unittest.TestCase):
    def test_named_registries_and_typed_union_discriminators(self):
        text = (CONTRACTS / "status-model.md").read_text(encoding="utf-8")
        machine = MachineContract(load_openapi_contract())
        names = {name: name for name in ("SchemaVersion", "ObjectType", "ErrorCode", "EventType")}
        names.update(BusinessValueKind="BusinessValue", MutationPayloadType="MutationPayload",
                     ConditionKind="Condition", ConditionValueTargetKind="ConditionValueTarget",
                     LocatorType="NativeAddress", AuditMetadataKind="AuditMetadata")
        for name, component in names.items():
            with self.subTest(enum=name):
                section = re.search(rf"^###\s+{name}\s*\n(.*?)(?=^###\s|\Z)", text, re.M | re.S)
                self.assertIsNotNone(section, f"missing semantic enum {name}")
                semantic = set(re.findall(r"`([^`]+)`", section.group(1)))
                self.assertTrue(semantic, f"no semantic vocabulary found for {name}")
                projected = machine.schemas[component]
                values = set(projected["enum"]) if "enum" in projected else set(projected["discriminator"]["mapping"])
                self.assertEqual(values, semantic)

    def test_failure_lineage_metadata_is_projected(self):
        schemas = MachineContract(load_openapi_contract()).schemas
        for name in ("ReplayMetadata", "ValidationMetadata"):
            self.assertIn("first_material_failure_event_id", schemas[name]["properties"])
            self.assertIs(schemas[name]["additionalProperties"], False)

    def test_contract_markdown_fences(self):
        for path in CONTRACTS.rglob("*.md"):
            with self.subTest(file=str(path.relative_to(CONTRACTS))):
                opening = None
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
                    if not marker:
                        continue
                    fence, tail = marker.groups()
                    if opening is None:
                        opening = (fence[0], len(fence), number)
                    elif fence[0] == opening[0] and len(fence) >= opening[1] and not tail.strip():
                        opening = None
                self.assertIsNone(opening, f"unclosed Markdown fence in {path}: {opening}")


if __name__ == "__main__":
    unittest.main()

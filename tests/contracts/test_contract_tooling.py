"""Negative infrastructure tests; these do not implement Foundation services."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from tools.contracts import validate_contract_fixtures as contract


class MachineRootTests(unittest.TestCase):
    def setUp(self):
        self.spec = {"openapi": "3.1.0", "components": {"schemas": {
            "Envelope": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
            "Record": {"allOf": [{"$ref": "#/components/schemas/Envelope"},
                {"type": "object", "properties": {"child": {"$ref": "#/components/schemas/Child"}}, "required": ["child"]}],
                "unevaluatedProperties": False},
            "Child": {"type": "object", "properties": {"value": {"type": "string"}},
                "required": ["value"], "additionalProperties": False},
        }}}

    def test_composed_root_resolves_nested_refs_and_preserves_closure(self):
        original = copy.deepcopy(self.spec)
        validator = contract.MachineContract(self.spec).validator("Record")
        good = {"id": "r", "child": {"value": "literal"}}
        self.assertEqual(list(validator.iter_errors(good)), [])
        self.assertTrue(list(validator.iter_errors({**good, "unknown": True})))
        self.assertTrue(list(validator.iter_errors({"id": "r", "child": {"value": "x", "unknown": True}})))
        self.assertTrue(list(validator.iter_errors({"id": "r"})))
        self.assertEqual(self.spec, original)

    def test_unresolvable_schema_pointer_is_not_ignored(self):
        self.spec["components"]["schemas"]["Child"] = {"$ref": "#/components/schemas/Missing"}
        with self.assertRaises(Exception):
            contract.MachineContract(self.spec)

    def test_jcs_numbers_and_utf16_order(self):
        self.assertEqual(contract.canonical([1.0, -0.0, 1e-7, 1e-6, 1e20, 1e21]),
                         '[1,0,1e-7,0.000001,100000000000000000000,1e+21]')
        self.assertEqual(contract.canonical({"\ue000": 2, "\U00010000": 1}), '{"\U00010000":1,"\ue000":2}')


class ReportingTests(unittest.TestCase):
    def test_broken_machine_root_still_writes_eight_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            with patch.object(contract, "MachineContract", side_effect=RuntimeError("broken root")), contextlib.redirect_stdout(io.StringIO()):
                exit_code = contract.main(["--report", str(path)])
            report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 1)
        self.assertEqual(len(report["scenarios"]), 8)
        self.assertTrue(all(row["validator_internal_result"] == "FAIL" for row in report["scenarios"]))

    def test_stage_exception_does_not_hide_other_dimensions(self):
        machine = contract.MachineContract(contract.load_openapi_contract())
        validator = contract.FixtureValidator(sorted(contract.EXAMPLES.glob("*.yaml"))[0], machine)
        with patch.object(validator, "validate_states", side_effect=RuntimeError("state checker defect")):
            result = validator.run()
        self.assertEqual(result["validator_internal_result"], "FAIL")
        self.assertEqual(result["state_machine_result"], "FAIL")
        for dimension in ("schema_result", "reference_result", "governance_result", "hash_result", "behavior_result"):
            self.assertEqual(result[dimension], "PASS", result)

    def test_all_fixtures_get_results_when_one_raises(self):
        original = contract.FixtureValidator.run
        def injected(instance):
            if instance.path.name.startswith("01-"):
                raise RuntimeError("injected validator defect")
            return original(instance)
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "contract-validation-report.json"
            with patch.object(contract.FixtureValidator, "run", injected), contextlib.redirect_stdout(io.StringIO()):
                exit_code = contract.main(["--report", str(report_path)])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 1)
            self.assertEqual(len(report["scenarios"]), 8)
            self.assertEqual(report["scenarios"][0]["validator_internal_result"], "FAIL")
            self.assertIn("VALIDATOR_INTERNAL", {e["category"] for e in report["scenarios"][0]["errors"]})

    def test_invalid_yaml_is_schema_failure_not_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.yaml"
            path.write_text("records: [", encoding="utf-8")
            result = contract.FixtureValidator(path, contract.MachineContract(contract.load_openapi_contract())).run()
        self.assertEqual(result["schema_result"], "FAIL")
        self.assertEqual(result["validator_internal_result"], "PASS")
        self.assertEqual(result["hash_result"], "NOT_EVALUATED")


class NegativeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.machine = contract.MachineContract(contract.load_openapi_contract())
        cls.fixtures = {path.name[:2]: yaml.safe_load(path.read_text(encoding="utf-8"))
                        for path in contract.EXAMPLES.glob("*.yaml")}

    def evaluate(self, change, scenario="01", rehash=False):
        data = copy.deepcopy(self.fixtures[scenario])
        change(data)
        if rehash:
            for event in data["audit_events"]:
                event["integrity_payload_hash"] = contract.digest({k: v for k, v in event.items() if k != "integrity_payload_hash"})
            for record in data["records"]:
                if record["object_type"] == "ApprovedChangeSet":
                    record["authorization_digest"] = contract.digest(record["authorization"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "negative.yaml"
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            return contract.FixtureValidator(path, self.machine).run()

    def assert_dimension_fails(self, result, dimension):
        self.assertEqual(result[dimension], "FAIL", result)
        self.assertEqual(result["overall_result"], "FAIL")
        self.assertEqual(result["validator_internal_result"], "PASS", result["errors"])

    def test_extra_missing_and_invalid_enum_fields(self):
        changes = [
            lambda d: d["records"][0].update(unknown=True),
            lambda d: d["records"][0].pop("created_at"),
            lambda d: d["records"][0].update(object_type="InventedType"),
            lambda d: d["audit_events"][0].update(event_type="InventedEvent"),
            lambda d: d["audit_events"][0].update(error_codes=["InventedError"]),
            lambda d: next(r for r in d["records"] if r["object_type"] == "FoundationTask").update(status="InventedStatus"),
            lambda d: next(a for a in d["actions"] if "replay_request" in a)["replay_request"].update(payload="unauthorized"),
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assert_dimension_fails(self.evaluate(change), "schema_result")

    def test_unresolved_reference_is_separate_from_schema(self):
        result = self.evaluate(lambda d: d["audit_events"][0]["output_refs"][0].update(object_id="missing"), rehash=True)
        self.assert_dimension_fails(result, "reference_result")
        self.assertEqual(result["schema_result"], "PASS")
        self.assertEqual(result["hash_result"], "PASS")

    def test_nullable_union_document_reference_is_checked(self):
        def change(d):
            event = next(e for e in d["audit_events"] if e["event_type"] == "EXECUTION_COMPLETED")
            event["metadata"]["output_document_version_ref"]["binary_hash"] = "0" * 64
        self.assert_dimension_fails(self.evaluate(change, rehash=True), "reference_result")

    def test_illegal_state_transition(self):
        def change(d):
            tasks = [r for r in d["records"] if r["object_type"] == "FoundationTask"]
            tasks[1]["status"] = "EXECUTING"
        self.assert_dimension_fails(self.evaluate(change), "state_machine_result")

    def test_behavior_assertions_are_checked(self):
        self.assert_dimension_fails(self.evaluate(lambda d: d["expected"].update(mutation_attempted=False)), "behavior_result")

    def test_approval_hash_is_checked(self):
        def change(d):
            next(r for r in d["records"] if r["object_type"] == "ApprovedChangeSet")["authorization_digest"] = "0" * 64
        self.assert_dimension_fails(self.evaluate(change), "hash_result")

    def test_causation_missing_cycle_and_cross_task_fail(self):
        for change in [
            lambda d: d["audit_events"][1].update(causation_event_id=None),
            lambda d: d["audit_events"][1].update(causation_event_id=d["audit_events"][1]["event_id"]),
            lambda d: d["audit_events"][1].update(task_id="another-task"),
        ]:
            with self.subTest(change=change):
                self.assert_dimension_fails(self.evaluate(change, rehash=True), "governance_result")

    def test_fuzzy_replay_and_ai_dispatch_fail(self):
        def fuzzy(d):
            next(a for a in d["actions"] if "replay_request" in a)["observations"]["fuzzy_fallback_attempted"] = True
        def ai(d):
            next(a for a in d["actions"] if "replay_request" in a)["actor"]["actor_type"] = "AI"
        for change in (fuzzy, ai):
            with self.subTest(change=change):
                self.assert_dimension_fails(self.evaluate(change), "governance_result")

    def test_recomputed_digest_does_not_approve_altered_payload(self):
        def change(d):
            next(r for r in d["records"] if r["object_type"] == "ApprovedChangeSet")["authorization"]["approved_changes"][0]["payload"]["replacement_text"] = "unreviewed"
        self.assert_dimension_fails(self.evaluate(change, rehash=True), "governance_result")

    def test_partial_task_cannot_release_even_if_expected_agrees(self):
        def change(d):
            task = [r for r in d["records"] if r["object_type"] == "FoundationTask"][-1]
            task.update(status="COMPLETED", release_status="ELIGIBLE")
            d["expected"].update(task_status="COMPLETED", release_status="ELIGIBLE")
        self.assert_dimension_fails(self.evaluate(change, scenario="02"), "governance_result")

    def test_duplicate_history_cannot_be_silently_overwritten(self):
        def change(d):
            d["records"].append(copy.deepcopy(d["records"][0]))
        self.assert_dimension_fails(self.evaluate(change), "reference_result")

    def test_hash_failure_does_not_fail_other_dimensions(self):
        spec = contract.MachineContract(contract.load_openapi_contract())
        source = sorted(contract.EXAMPLES.glob("*.yaml"))[0]
        with tempfile.TemporaryDirectory() as tmp:
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
            data["audit_events"][0]["integrity_payload_hash"] = "0" * 64
            path = Path(tmp) / source.name
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
            result = contract.FixtureValidator(path, spec).run()
        self.assertEqual(result["hash_result"], "FAIL")
        self.assertEqual(result["schema_result"], "PASS")
        self.assertEqual(result["reference_result"], "PASS")

    def test_machine_validation_does_not_read_markdown(self):
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            if path.suffix == ".md":
                raise AssertionError("Markdown must not decide fixture machine validity")
            return original(path, *args, **kwargs)
        with patch.object(Path, "read_text", guarded):
            machine = contract.MachineContract(contract.load_openapi_contract())
            result = contract.FixtureValidator(sorted(contract.EXAMPLES.glob("*.yaml"))[0], machine).run()
        self.assertEqual(result["validator_internal_result"], "PASS")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate Foundation Contract v0.1 behavioral fixtures.

This is contract tooling. It validates persisted fixture data and does not
implement Foundation runtime behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, RefResolver

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "docs" / "contracts"
EXAMPLES = CONTRACTS / "examples"
SCHEMA_VERSION = "0.1.0"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
TARGET_RE = re.compile(r"^[A-Z][A-Z0-9_.]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
DECIMAL_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
INTEGER_RE = re.compile(r"^-?(?:0|[1-9]\d*)$")

REUSABLE_TYPES = {
    "TargetContractDefinition", "TargetRegionDefinition", "RulePack",
    "BusinessRule", "FreshnessPolicy", "SourceRequirement", "ValidationPlan",
}
TASK_BOUNDARY_REF_TYPES = {
    "DocumentArtifact", "DocumentVersion", "DocumentPreflightAssessment", "PerceptionSnapshot",
    "SemanticObject", "NativeLocator", "NativeBinding", "TargetContractInstance", "TargetRegion",
    "RuleEvaluation", "SourceAssessment", "EvidenceRecord", "EvidenceCheck", "EvidenceAssessment",
    "MappingProposal", "AIInteractionRecord", "ChangeProposal", "ReviewDecision", "ApprovedChangeSet",
    "ExecutionResult", "ChangeExecutionResult", "ValidationReport", "ValidationCheckResult",
    "ExceptionRecord", "AnalysisRun",
}
EVENT_METADATA_KIND = {
    "TASK_CREATED": "GOVERNANCE", "DOCUMENT_REGISTERED": "GOVERNANCE",
    "DOCUMENT_PREFLIGHT_COMPLETED": "DETERMINISTIC_EVALUATION",
    "PERCEPTION_COMPLETED": "PERCEPTION", "PERCEPTION_FAILED": "PERCEPTION",
    "NATIVE_BINDING_ASSESSED": "NATIVE_BINDING", "ANALYSIS_COMPLETED": "GOVERNANCE",
    "RULE_EVALUATED": "DETERMINISTIC_EVALUATION", "SOURCE_ASSESSED": "DETERMINISTIC_EVALUATION",
    "EVIDENCE_CHECKED": "DETERMINISTIC_EVALUATION", "EVIDENCE_ASSESSED": "DETERMINISTIC_EVALUATION",
    "AI_INTERACTION_RECORDED": "AI_INTERACTION", "MAPPING_PROPOSED": "GOVERNANCE",
    "CHANGE_PROPOSED": "GOVERNANCE", "REVIEW_DECIDED": "GOVERNANCE", "SOURCE_REQUESTED": "GOVERNANCE",
    "DECISION_SUPERSEDED": "GOVERNANCE", "CHANGE_SET_APPROVED": "GOVERNANCE",
    "APPROVAL_INVALIDATED": "GOVERNANCE", "APPROVAL_REVOKED": "GOVERNANCE", "REPLAY_REQUESTED": "REPLAY",
    "EXECUTION_COMPLETED": "REPLAY", "EXECUTION_REFUSED": "REPLAY", "VALIDATION_COMPLETED": "VALIDATION",
    "RELEASE_ELIGIBILITY_CONFIRMED": "GOVERNANCE", "RELEASE_WITHHELD": "GOVERNANCE",
    "OUTPUT_RELEASED": "GOVERNANCE", "STATUS_TRANSITIONED": "GOVERNANCE",
    "OUTPUT_QUARANTINED": "VALIDATION", "EXCEPTION_RECORDED": "EXCEPTION", "EXCEPTION_RESOLVED": "EXCEPTION",
}
EVENT_ACTOR_TYPES = {
    "TASK_CREATED": {"SYSTEM", "HUMAN"}, "DOCUMENT_REGISTERED": {"SYSTEM"},
    "ANALYSIS_COMPLETED": {"SYSTEM"}, "CHANGE_PROPOSED": {"SYSTEM"}, "REVIEW_DECIDED": {"HUMAN"},
    "SOURCE_REQUESTED": {"HUMAN"}, "DECISION_SUPERSEDED": {"HUMAN", "SYSTEM"},
    "CHANGE_SET_APPROVED": {"SYSTEM"}, "APPROVAL_INVALIDATED": {"SYSTEM"}, "APPROVAL_REVOKED": {"HUMAN", "SYSTEM"},
    "RELEASE_ELIGIBILITY_CONFIRMED": {"SYSTEM"}, "RELEASE_WITHHELD": {"SYSTEM"}, "OUTPUT_RELEASED": {"SYSTEM"},
    "STATUS_TRANSITIONED": {"SYSTEM", "HUMAN"}, "AI_INTERACTION_RECORDED": {"AI"}, "REPLAY_REQUESTED": {"SYSTEM"},
    "EXECUTION_COMPLETED": {"REPLAY_ENGINE"}, "EXECUTION_REFUSED": {"REPLAY_ENGINE"},
    "VALIDATION_COMPLETED": {"VALIDATOR"}, "OUTPUT_QUARANTINED": {"SYSTEM", "VALIDATOR"},
    "DOCUMENT_PREFLIGHT_COMPLETED": {"SYSTEM"}, "PERCEPTION_COMPLETED": {"SYSTEM"}, "PERCEPTION_FAILED": {"SYSTEM"},
    "NATIVE_BINDING_ASSESSED": {"SYSTEM"}, "RULE_EVALUATED": {"SYSTEM"}, "SOURCE_ASSESSED": {"SYSTEM"},
    "EVIDENCE_CHECKED": {"SYSTEM"}, "EVIDENCE_ASSESSED": {"SYSTEM"}, "MAPPING_PROPOSED": {"SYSTEM"},
}
TASK_EDGES = {
    "CREATED": {"ANALYZING", "CANCELLED"}, "ANALYZING": {"AWAITING_REVIEW", "BLOCKED", "FAILED", "CANCELLED"},
    "AWAITING_REVIEW": {"READY_FOR_EXECUTION", "BLOCKED", "CANCELLED"},
    "READY_FOR_EXECUTION": {"EXECUTING", "BLOCKED", "CANCELLED"},
    "EXECUTING": {"VALIDATING", "BLOCKED", "FAILED"}, "VALIDATING": {"COMPLETED", "BLOCKED", "FAILED"},
    "BLOCKED": {"ANALYZING", "AWAITING_REVIEW", "READY_FOR_EXECUTION", "CANCELLED"},
}
MATERIAL_EVENT_MAP = {
    "AnalysisRun": "ANALYSIS_COMPLETED", "RuleEvaluation": "RULE_EVALUATED",
    "SourceAssessment": "SOURCE_ASSESSED", "EvidenceCheck": "EVIDENCE_CHECKED",
    "EvidenceAssessment": "EVIDENCE_ASSESSED", "DocumentPreflightAssessment": "DOCUMENT_PREFLIGHT_COMPLETED",
    "PerceptionSnapshot": "PERCEPTION_COMPLETED", "NativeBinding": "NATIVE_BINDING_ASSESSED",
    "AIInteractionRecord": "AI_INTERACTION_RECORDED",
}

def section(text: str, heading: str) -> str:
    match = re.search(rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)",
                      text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def enum_registry() -> dict[str, set[str]]:
    text = (CONTRACTS / "status-model.md").read_text(encoding="utf-8")
    result: dict[str, set[str]] = {}
    tick = chr(96)
    for name in re.findall(r"^### ([A-Za-z][A-Za-z0-9_]*)\s*$", text, flags=re.MULTILINE):
        values = re.findall(tick + r"([^" + tick + r"]+)" + tick, section(text, name))
        if values:
            result[name] = set(values)
    return result


def load_openapi_contract() -> dict[str, Any]:
    """Load the machine projection; field shape authority lives there."""
    spec = yaml.safe_load((CONTRACTS / "foundation.openapi.yaml").read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or spec.get("openapi") != "3.1.0":
        raise ValueError("foundation.openapi.yaml must be OpenAPI 3.1.0")
    return spec


def canonical(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite number")
        if value == 0:
            return "0"
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(canonical(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value, key=lambda item: item.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False, separators=(",", ":")) + ":" + canonical(value[k])
                             for k in keys) + "}"
    raise TypeError(f"unsupported JSON value: {type(value)!r}")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class FixtureValidator:
    def __init__(self, path: Path, enums: dict[str, set[str]],
                 openapi: dict[str, Any]):
        self.path, self.enums, self.openapi = path, enums, openapi
        self.openapi_resolver = RefResolver.from_schema(openapi)
        self.data: dict[str, Any] = {}
        self.errors: list[dict[str, str]] = []
        self.records: dict[tuple[str, str, int], dict[str, Any]] = {}
        self.events: dict[tuple[str, int], dict[str, Any]] = {}
        self.content_refs: set[tuple[str, str, str]] = set()
        self.versions: dict[tuple[str, str, str], dict[str, Any]] = {}

    @property
    def scenario(self) -> str:
        return str(self.data.get("scenario_id", self.path.stem))

    def error(self, path: str, message: str) -> None:
        self.errors.append({"path": path, "message": message})

    def exact(self, value: Any, required: set[str], optional: set[str], path: str) -> bool:
        if not isinstance(value, dict):
            self.error(path, "expected object")
            return False
        keys = set(value)
        missing, extra = sorted(required - keys), sorted(keys - required - optional)
        if missing:
            self.error(path, "missing fields: " + ", ".join(missing))
        if extra:
            self.error(path, "unknown fields: " + ", ".join(extra))
        return not missing and not extra

    def enum(self, value: Any, name: str, path: str) -> None:
        if name in self.enums and value not in self.enums[name]:
            self.error(path, f"{value!r} is not in {name}")

    def primitive(self, value: Any, type_name: str, path: str) -> None:
        if type_name in self.enums:
            self.enum(value, type_name, path)
            return
        if type_name in {"Text", "ExactText", "NullableText", "EvaluatorKey"}:
            if not isinstance(value, str) or (type_name != "ExactText" and not value):
                self.error(path, f"expected {type_name}")
            return
        if type_name == "ID" and (not isinstance(value, str) or not ID_RE.fullmatch(value)):
            self.error(path, "invalid ID")
        elif type_name == "BusinessTargetID" and (not isinstance(value, str) or not TARGET_RE.fullmatch(value)):
            self.error(path, "invalid BusinessTargetID")
        elif type_name == "SHA256" and (not isinstance(value, str) or not SHA_RE.fullmatch(value)):
            self.error(path, "invalid SHA-256")
        elif type_name == "URI" and (not isinstance(value, str) or not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)):
            self.error(path, "URI must be absolute")
        elif type_name == "LocalDate" and (not isinstance(value, str) or not DATE_RE.fullmatch(value)):
            self.error(path, "invalid LocalDate")
        elif type_name == "Timestamp" and (not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value)):
            self.error(path, "invalid UTC Timestamp")
        elif type_name == "DecimalString" and (not isinstance(value, str) or not DECIMAL_RE.fullmatch(value)):
            self.error(path, "invalid DecimalString")
        elif type_name == "IntegerString" and (not isinstance(value, str) or not INTEGER_RE.fullmatch(value)):
            self.error(path, "invalid IntegerString")
        elif type_name == "CurrencyCode" and (not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value)):
            self.error(path, "invalid CurrencyCode")
        elif type_name in {"PositiveInt", "NonNegativeInt"}:
            if isinstance(value, bool) or not isinstance(value, int) or value < (1 if type_name == "PositiveInt" else 0):
                self.error(path, f"invalid {type_name}")
        elif type_name == "Bool" and not isinstance(value, bool):
            self.error(path, "expected boolean")
        elif type_name == "CellAddress" and (not isinstance(value, str) or not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", value)):
            self.error(path, "invalid CellAddress")
        elif type_name == "RangeAddress" and (not isinstance(value, str) or not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*", value)):
            self.error(path, "invalid RangeAddress")
        elif type_name not in {
            "StructuredData", "Nullable", "SchemaVersion", "ObjectType", "Reference",
            "DocumentVersionRef", "SemanticReference", "ContentRef", "EvaluatorBinding",
            "Actor", "BusinessValue", "CapabilityResult", "CapabilityResultRef",
            "PreflightFinding", "NativeAddress", "Condition", "ConditionValueTarget",
            "FreshnessEvaluation", "ProtectedScope", "ValidationRequirement",
            "AuthorizationBinding", "Period", "MutationPayload", "NativePathStep",
            "NativeElementPath", "ApprovedChange",
        }:
            self.error(path, "unhandled contract type " + type_name)

    def validate_ref(self, value: Any, path: str) -> None:
        if not self.exact(value, {"object_type", "object_id", "revision"}, set(), path):
            return
        self.primitive(value["object_id"], "ID", path + ".object_id")
        self.primitive(value["revision"], "PositiveInt", path + ".revision")
        typ = value["object_type"]
        if typ not in self.enums.get("ObjectType", set()) and typ != "AuditEvent":
            self.error(path, "invalid reference object_type")
        elif typ == "AuditEvent":
            if (value["object_id"], value["revision"]) not in self.events:
                self.error(path, "unresolved AuditEvent reference")
        elif (typ, value["object_id"], value["revision"]) not in self.records:
            self.error(path, "unresolved record reference")

    def validate_content(self, value: Any, path: str) -> None:
        if not self.exact(value, {"uri", "sha256", "media_type"}, set(), path):
            return
        self.primitive(value["uri"], "URI", path + ".uri")
        self.primitive(value["sha256"], "SHA256", path + ".sha256")
        self.primitive(value["media_type"], "Text", path + ".media_type")
        if (value["uri"], value["sha256"], value["media_type"]) not in self.content_refs:
            self.error(path, "ContentRef is not declared in facts.artifacts")

    def validate_document_ref(self, value: Any, path: str) -> None:
        if not self.exact(value, {"document_id", "version_id", "binary_hash"}, set(), path):
            return
        self.primitive(value["document_id"], "ID", path + ".document_id")
        self.primitive(value["version_id"], "ID", path + ".version_id")
        self.primitive(value["binary_hash"], "SHA256", path + ".binary_hash")
        if (value["document_id"], value["version_id"], value["binary_hash"]) not in self.versions:
            self.error(path, "DocumentVersionRef does not match DocumentVersion")

    def validate_evaluator(self, value: Any, path: str) -> None:
        """Check semantic binding resolution; shape is projected by OpenAPI."""
        if not isinstance(value, dict):
            self.error(path, "EvaluatorBinding must be an object")
            return
        for key in ("evaluator_key", "evaluator_version", "configuration_ref"):
            if key not in value:
                self.error(path, "missing evaluator binding field: " + key)
        if "configuration_ref" in value:
            self.validate_content(value["configuration_ref"], path + ".configuration_ref")

    def validate_freshness_evaluation(self, value: Any, path: str) -> None:
        """Validate references and evaluator identity; field shape is OpenAPI-owned."""
        if not isinstance(value, dict):
            self.error(path, "FreshnessEvaluation must be an object")
            return
        if "freshness_policy_ref" in value:
            self.validate_ref(value["freshness_policy_ref"], path + ".freshness_policy_ref")
        for index, ref in enumerate(value.get("document_version_refs", [])):
            self.validate_document_ref(ref, f"{path}.document_version_refs[{index}]")
        for index, ref in enumerate(value.get("input_refs", [])):
            self.validate_content(ref, f"{path}.input_refs[{index}]")
        if "evaluator_key" in value and not isinstance(value["evaluator_key"], str):
            self.error(path + ".evaluator_key", "evaluator_key must be text")
        if "evaluator_version" in value and not isinstance(value["evaluator_version"], str):
            self.error(path + ".evaluator_version", "evaluator_version must be text")

    def validate_condition_semantics(self, value: Any, path: str) -> None:
        """Check cross-field condition rules without duplicating union schemas."""
        if not isinstance(value, dict):
            return
        kind = value.get("kind")
        if kind == "BINARY_HASH_EQUALS":
            document_ref = value.get("document_version_ref", {})
            if isinstance(document_ref, dict) and value.get("expected_binary_hash") != document_ref.get("binary_hash"):
                self.error(path, "binary hash condition does not equal its pinned document hash")
            if isinstance(document_ref, dict):
                self.validate_document_ref(document_ref, path + ".document_version_ref")
        elif kind == "TEXT_EQUALS":
            target = value.get("target", {})
            if isinstance(target, dict) and target.get("kind") == "INPUT_NATIVE_OBJECT":
                self.validate_ref(target.get("native_locator_ref"), path + ".target.native_locator_ref")
        elif kind == "VALUE_EQUALS":
            target = value.get("target", {})
            if isinstance(target, dict) and target.get("kind") == "INPUT_NATIVE_OBJECT":
                self.validate_ref(target.get("native_locator_ref"), path + ".target.native_locator_ref")
            if "value_reader_policy_ref" in value:
                self.validate_content(value["value_reader_policy_ref"], path + ".value_reader_policy_ref")
        elif kind == "CAPABILITY_SUPPORTED":
            self.validate_ref(value.get("native_locator_ref"), path + ".native_locator_ref")
            capability_ref = value.get("capability_result_ref", {})
            if isinstance(capability_ref, dict):
                self.validate_ref(capability_ref.get("preflight_assessment_ref"), path + ".capability_result_ref.preflight_assessment_ref")
        elif kind == "EVIDENCE_VERIFIED":
            self.validate_ref(value.get("evidence_assessment_ref"), path + ".evidence_assessment_ref")
        elif kind == "PRESERVE_SCOPE":
            scope = value.get("protected_scope", {})
            if isinstance(scope, dict) and scope.get("preserve_outside_approved_changes") is not True:
                self.error(path, "preserve scope must retain all non-approved content")

    def validate_approved_change_semantics(self, value: Any, path: str) -> None:
        """Validate inline authorization references and cross-field gates."""
        if not isinstance(value, dict):
            return
        for field in ("change_proposal_ref", "native_locator_ref", "review_decision_ref"):
            if field in value:
                self.validate_ref(value[field], f"{path}.{field}")
        for index, ref in enumerate(value.get("evidence_refs", [])):
            self.validate_ref(ref, f"{path}.evidence_refs[{index}]")
        for field in ("preconditions", "postconditions"):
            for index, condition in enumerate(value.get(field, [])):
                self.validate_condition_semantics(condition, f"{path}.{field}[{index}]")

    def validate_authorization_semantics(self, value: Any, path: str) -> None:
        """Resolve authorization references without defining another field schema."""
        if not isinstance(value, dict):
            return
        if "target_document_version_ref" in value:
            self.validate_document_ref(value["target_document_version_ref"], path + ".target_document_version_ref")
        for index, ref in enumerate(value.get("source_document_version_refs", [])):
            self.validate_document_ref(ref, f"{path}.source_document_version_refs[{index}]")
        expected_types = {
            "target_contract_definition_ref": "TargetContractDefinition",
            "target_contract_instance_ref": "TargetContractInstance",
            "rule_pack_ref": "RulePack",
            "validation_plan_ref": "ValidationPlan",
        }
        for field, expected_type in expected_types.items():
            ref = value.get(field)
            self.validate_ref(ref, f"{path}.{field}")
            if isinstance(ref, dict) and ref.get("object_type") != expected_type:
                self.error(f"{path}.{field}", f"expected {expected_type} reference")
        list_types = {
            "source_assessment_refs": "SourceAssessment",
            "evidence_assessment_refs": "EvidenceAssessment",
            "review_decision_refs": "ReviewDecision",
        }
        for field, expected_type in list_types.items():
            for index, ref in enumerate(value.get(field, [])):
                self.validate_ref(ref, f"{path}.{field}[{index}]")
                if isinstance(ref, dict) and ref.get("object_type") != expected_type:
                    self.error(f"{path}.{field}[{index}]", f"expected {expected_type} reference")
        identifiers: set[str] = set()
        for index, change in enumerate(value.get("approved_changes", [])):
            change_path = f"{path}.approved_changes[{index}]"
            self.validate_approved_change_semantics(change, change_path)
            identifier = change.get("approved_change_id") if isinstance(change, dict) else None
            if identifier in identifiers:
                self.error(path, "duplicate approved_change_id")
            identifiers.add(identifier)
        scope = value.get("protected_scope")
        if isinstance(scope, dict):
            if scope.get("preserve_outside_approved_changes") is not True:
                self.error(path + ".protected_scope", "protected scope must preserve outside approved changes")
            if "document_version_ref" in scope:
                self.validate_document_ref(scope["document_version_ref"], path + ".protected_scope.document_version_ref")
            for index, ref in enumerate(scope.get("protected_locator_refs", [])):
                self.validate_ref(ref, f"{path}.protected_scope.protected_locator_refs[{index}]")
        for index, ref in enumerate(value.get("qualification_refs", [])):
            self.validate_content(ref, f"{path}.qualification_refs[{index}]")

    def validate_period(self, value: Any, path: str) -> None:
        if self.exact(value, {"label", "start_date", "end_date"}, set(), path):
            self.primitive(value["label"], "Text", path + ".label")
            self.primitive(value["start_date"], "LocalDate", path + ".start_date")
            self.primitive(value["end_date"], "LocalDate", path + ".end_date")

    def validate_actor(self, value: Any, path: str) -> None:
        if self.exact(value, {"actor_type", "actor_id"}, set(), path):
            self.primitive(value["actor_type"], "ActorType", path + ".actor_type")
            self.primitive(value["actor_id"], "ID", path + ".actor_id")

    def load(self) -> None:
        try:
            loaded = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.error("$", "YAML parse failed: " + str(exc))
            return
        if not isinstance(loaded, dict):
            self.error("$", "fixture must be an object")
            return
        self.data = loaded
        top_level = {"schema_version", "fixture_type", "scenario_id", "title", "facts",
                     "records", "actions", "audit_events", "expected"}
        self.exact(self.data, top_level, set(), "$")
        if self.data.get("schema_version") != SCHEMA_VERSION:
            self.error("$.schema_version", "must be contract schema version 0.1.0")
        if self.data.get("fixture_type") != "CONTRACT_SCENARIO":
            self.error("$.fixture_type", "must be CONTRACT_SCENARIO")
        facts = self.data.get("facts", {})
        if not isinstance(facts, dict):
            self.error("$.facts", "must be an object")
            facts = {}
        for item in facts.get("artifacts", []) or []:
            ref = item.get("ref") if isinstance(item, dict) else None
            if isinstance(ref, dict) and {"uri", "sha256", "media_type"} <= set(ref):
                self.content_refs.add((ref["uri"], ref["sha256"], ref["media_type"]))
        records = self.data.get("records", [])
        if not isinstance(records, list):
            self.error("$.records", "must be an array")
            return
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                self.error(f"$.records[{index}]", "must be an object")
                continue
            typ, rid, revision = record.get("object_type"), record.get("id"), record.get("revision")
            if typ not in self.enums.get("ObjectType", set()):
                self.error(f"$.records[{index}].object_type", "invalid ObjectType")
            if isinstance(revision, int) and not isinstance(revision, bool):
                self.records[(typ, rid, revision)] = record
                if typ == "DocumentVersion":
                    self.versions[(record.get("document_id"), rid, record.get("binary_hash"))] = record
        for event in self.data.get("audit_events", []) or []:
            if isinstance(event, dict):
                self.events[(event.get("event_id"), event.get("event_version"))] = event
        expected = self.data.get("expected", {})
        expected_fields = {"task_ref", "task_status", "release_status", "first_material_failure_event_id",
                           "ai_execution_authority", "fuzzy_fallback_attempted", "mutation_attempted",
                           "approved_change_set_refs", "execution_refs", "validation_report_refs",
                           "error_codes", "targets", "output_document_ref", "output_document_status",
                           "preserved_record_refs", "new_correlation_id"}
        required_expected = {"task_ref", "task_status", "release_status", "first_material_failure_event_id",
                             "ai_execution_authority", "fuzzy_fallback_attempted", "mutation_attempted",
                             "approved_change_set_refs", "execution_refs", "validation_report_refs", "error_codes", "targets"}
        if isinstance(expected, dict):
            self.exact(expected, required_expected, expected_fields - required_expected, "$.expected")
        else:
            self.error("$.expected", "must be an object")

    def validate_records(self) -> None:
        for index, record in enumerate(self.data.get("records", []) or []):
            if not isinstance(record, dict):
                continue
            typ = record.get("object_type")
            schema = self.openapi.get("components", {}).get("schemas", {}).get(typ)
            if not schema:
                self.error(f"$.records[{index}]", "no OpenAPI schema for ObjectType")
                continue
            validator = Draft202012Validator(schema, resolver=self.openapi_resolver)
            for issue in sorted(validator.iter_errors(record), key=lambda error: list(error.path)):
                location = ".".join(str(part) for part in issue.path)
                self.error(f"$.records[{index}]" + ("." + location if location else ""),
                           "OpenAPI schema: " + issue.message)
            self.validate_closed_record_keys(typ, record, f"$.records[{index}]")
            self.validate_schema_refs(schema, record, f"$.records[{index}]")
            if typ in REUSABLE_TYPES:
                if "task_id" in record:
                    self.error(f"$.records[{index}].task_id", "reusable definition must not carry task_id")
                self.validate_reusable_boundary(record, f"$.records[{index}]")
            if typ != "FoundationTask" and typ not in REUSABLE_TYPES:
                task_records = [r for r in self.records.values() if r.get("object_type") == "FoundationTask"]
                if task_records and record.get("task_id") != task_records[0].get("id"):
                    self.error(f"$.records[{index}].task_id", "must reference FoundationTask")
            if typ == "DocumentVersion" and record.get("content_ref", {}).get("sha256") != record.get("binary_hash"):
                self.error(f"$.records[{index}]", "DocumentVersion content hash mismatch")
            if typ == "DocumentVersion" and record.get("revision") != 1:
                self.error(f"$.records[{index}].revision", "DocumentVersion revision must remain 1")
            if typ in {
                "DocumentPreflightAssessment", "TargetContractInstance", "TargetRegion",
                "NativeLocator", "ChangeProposal", "ExecutionResult", "ValidationReport",
            } and "document_version_ref" in record:
                self.validate_document_ref(record["document_version_ref"], f"$.records[{index}].document_version_ref")
            if typ in {"ChangeProposal", "ExecutionResult", "ValidationReport"} and "input_document_version_ref" in record:
                self.validate_document_ref(record["input_document_version_ref"], f"$.records[{index}].input_document_version_ref")
            if typ == "TargetContractInstance" and "target_document_version_ref" in record:
                self.validate_document_ref(record["target_document_version_ref"], f"$.records[{index}].target_document_version_ref")
            if typ == "ApprovedChangeSet" and record.get("authorization", {}).get("target_document_version_ref") is not None:
                self.validate_document_ref(record["authorization"]["target_document_version_ref"], f"$.records[{index}].authorization.target_document_version_ref")
            if typ in {"ExecutionResult", "ValidationReport"} and "output_document_version_ref" in record:
                output_version = record["output_document_version_ref"]
                if output_version is not None:
                    self.validate_document_ref(output_version, f"$.records[{index}].output_document_version_ref")
            if typ == "DocumentPreflightAssessment":
                for cap_index, capability in enumerate(record.get("capability_results", [])):
                    if isinstance(capability, dict) and "document_version_ref" in capability:
                        self.validate_document_ref(capability["document_version_ref"], f"$.records[{index}].capability_results[{cap_index}].document_version_ref")
                    if isinstance(capability, dict):
                        compatible = {
                            "REPLACE_RUN_TEXT": {"DOCX_RUN"},
                            "REPLACE_SDT_TEXT": {"DOCX_CONTENT_CONTROL"},
                            "REPLACE_SIMPLE_TABLE_CELL_TEXT": {"DOCX_TABLE_CELL"},
                        }.get(capability.get("operation"))
                        if compatible and capability.get("native_structure") not in compatible:
                            self.error(f"$.records[{index}].capability_results[{cap_index}]", "capability operation and native structure are incompatible")
                        if capability.get("status") == "SUPPORTED" and not capability.get("qualification_evidence_refs"):
                            self.error(f"$.records[{index}].capability_results[{cap_index}]", "SUPPORTED capability requires qualification evidence")
            if typ == "TargetRegion":
                for cap_index, capability_ref in enumerate(record.get("capability_result_refs", [])):
                    if not isinstance(capability_ref, dict):
                        continue
                    preflight_ref = capability_ref.get("preflight_assessment_ref")
                    self.validate_ref(preflight_ref, f"$.records[{index}].capability_result_refs[{cap_index}].preflight_assessment_ref")
                    if isinstance(preflight_ref, dict):
                        if preflight_ref.get("object_type") != "DocumentPreflightAssessment":
                            self.error(f"$.records[{index}].capability_result_refs[{cap_index}].preflight_assessment_ref", "capability assessment must reference DocumentPreflightAssessment")
                        assessment = self.records.get((preflight_ref.get("object_type"), preflight_ref.get("object_id"), preflight_ref.get("revision")))
                        if assessment and not any(item.get("capability_result_id") == capability_ref.get("capability_result_id") for item in assessment.get("capability_results", [])):
                            self.error(f"$.records[{index}].capability_result_refs[{cap_index}]", "capability result is absent from its preflight assessment")
            if typ == "FreshnessEvaluation":
                self.validate_freshness_evaluation(record, f"$.records[{index}]")
            if typ == "ApprovedChangeSet":
                self.validate_authorization_semantics(record.get("authorization"), f"$.records[{index}].authorization")
            if typ == "NativeLocator" and record.get("locator_type") != record.get("address", {}).get("kind"):
                self.error(f"$.records[{index}]", "locator_type and typed address kind must match")
            if typ == "TargetRegion" and "capability_status" in record:
                self.error(f"$.records[{index}]", "flattened capability_status is forbidden")
            if typ == "SourceRequirement":
                policy = record.get("period_policy")
                if policy == "SPECIFIC_PERIOD" and "specific_period" not in record:
                    self.error(f"$.records[{index}]", "SPECIFIC_PERIOD requires specific_period")
                if policy != "SPECIFIC_PERIOD" and "specific_period" in record:
                    self.error(f"$.records[{index}]", "specific_period is forbidden")
            if typ == "SourceAssessment" and record.get("outcome") == "SUFFICIENT":
                if record.get("freshness_evaluation", {}).get("outcome") != "PASS":
                    self.error(f"$.records[{index}]", "SUFFICIENT requires passing freshness")
            if typ == "SourceAssessment" and record.get("freshness_evaluation") is not None:
                self.validate_freshness_evaluation(record["freshness_evaluation"], f"$.records[{index}].freshness_evaluation")
            if typ == "EvidenceCheck":
                if record.get("check_kind") == "FRESHNESS" and "freshness_evaluation" not in record:
                    self.error(f"$.records[{index}]", "FRESHNESS requires freshness_evaluation")
                if record.get("check_kind") != "FRESHNESS" and "freshness_evaluation" in record:
                    self.error(f"$.records[{index}]", "only FRESHNESS may carry freshness_evaluation")
                if record.get("freshness_evaluation") is not None:
                    self.validate_freshness_evaluation(record["freshness_evaluation"], f"$.records[{index}].freshness_evaluation")
                    if record.get("outcome") != record["freshness_evaluation"].get("outcome"):
                        self.error(f"$.records[{index}]", "freshness check outcome must equal freshness evaluation outcome")
            if typ == "ReviewDecision":
                requested = record.get("requested_source_requirement_refs", [])
                if record.get("outcome") == "REQUEST_MORE_SOURCE" and not requested:
                    self.error(f"$.records[{index}]", "REQUEST_MORE_SOURCE requires source references")
                if record.get("outcome") != "REQUEST_MORE_SOURCE" and requested:
                    self.error(f"$.records[{index}]", "only REQUEST_MORE_SOURCE may request source")

    def _schema_parts(self, node: Any) -> tuple[set[str], set[str]]:
        if not isinstance(node, dict):
            return set(), set()
        if "$ref" in node:
            with self.openapi_resolver.resolving(node["$ref"]) as resolved:
                return self._schema_parts(resolved)
        props = set(node.get("properties", {}))
        required = set(node.get("required", []))
        for child in node.get("allOf", []) or []:
            c_props, c_required = self._schema_parts(child)
            props |= c_props
            required |= c_required
        return props, required

    def validate_closed_record_keys(self, typ: str, record: dict[str, Any], path: str) -> None:
        allowed, required = self._schema_parts(self.openapi["components"]["schemas"][typ])
        missing, extra = sorted(required - set(record)), sorted(set(record) - allowed)
        if missing:
            self.error(path, "missing fields: " + ", ".join(missing))
        if extra:
            self.error(path, "unknown fields: " + ", ".join(extra))

    def validate_schema_refs(self, node: Any, value: Any, path: str) -> None:
        """Resolve references by following the OpenAPI projection, not a second field map."""
        if value is None or not isinstance(node, dict):
            return
        if "$ref" in node:
            ref_name = node["$ref"].rsplit("/", 1)[-1]
            if ref_name in {"Ref", "Reference"}:
                self.validate_ref(value, path)
                return
            if ref_name == "DocumentVersionRef":
                self.validate_document_ref(value, path)
                return
            if ref_name == "ContentRef":
                self.validate_content(value, path)
                return
            if ref_name == "EvaluatorBinding":
                self.validate_evaluator(value, path)
                return
            if ref_name == "FreshnessEvaluation":
                self.validate_freshness_evaluation(value, path)
                return
            with self.openapi_resolver.resolving(node["$ref"]) as resolved:
                self.validate_schema_refs(resolved, value, path)
            return
        if "allOf" in node:
            for child in node.get("allOf", []):
                self.validate_schema_refs(child, value, path)
        if "oneOf" in node:
            branches = node.get("oneOf", [])
            discriminator = node.get("discriminator", {}).get("propertyName")
            selected = []
            if discriminator and isinstance(value, dict) and value.get(discriminator) is not None:
                wanted = value.get(discriminator)
                mapping = node.get("discriminator", {}).get("mapping", {})
                if wanted in mapping:
                    selected = [{"$ref": mapping[wanted]}]
            if not selected:
                for branch in branches:
                    if not isinstance(branch, dict):
                        continue
                    branch_node = branch
                    if "$ref" in branch:
                        with self.openapi_resolver.resolving(branch["$ref"]) as resolved:
                            branch_node = resolved
                    const = branch_node.get("properties", {}).get(discriminator or "kind", {}).get("const")
                    if const is not None and isinstance(value, dict) and value.get(discriminator or "kind") == const:
                        selected.append(branch)
            for branch in selected:
                self.validate_schema_refs(branch, value, path)
            return
        if "properties" in node and isinstance(value, dict):
            for key, child in node.get("properties", {}).items():
                if key in value:
                    self.validate_schema_refs(child, value[key], f"{path}.{key}")
        if "items" in node and isinstance(value, list):
            for index, item in enumerate(value):
                self.validate_schema_refs(node["items"], item, f"{path}[{index}]")

    def validate_reusable_boundary(self, value: Any, path: str, root: bool = True) -> None:
        if isinstance(value, dict):
            if not root and {"object_type", "object_id", "revision"} <= set(value):
                if value.get("object_type") in TASK_BOUNDARY_REF_TYPES:
                    self.error(path, "reusable definition references task-owned object")
                return
            for key, child in value.items():
                self.validate_reusable_boundary(child, f"{path}.{key}", False)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self.validate_reusable_boundary(child, f"{path}[{index}]", False)

    def validate_metadata(self, metadata: Any, path: str) -> None:
        if not isinstance(metadata, dict):
            self.error(path, "metadata must be an object")
            return
        kind = metadata.get("metadata_kind")
        self.enum(kind, "AuditMetadataKind", path + ".metadata_kind")
        if kind not in self.enums.get("AuditMetadataKind", set()):
            return
        if "summary" in metadata:
            self.primitive(metadata["summary"], "Text", path + ".summary")
        if kind == "GOVERNANCE":
            for name in ("prior_status", "resulting_status"):
                if metadata.get(name) is not None:
                    self.primitive(metadata[name], "Text", path + "." + name)
            if "decision_ref" in metadata:
                self.validate_ref(metadata["decision_ref"], path + ".decision_ref")
        elif kind == "PERCEPTION":
            self.validate_ref(metadata["analysis_run_ref"], path + ".analysis_run_ref")
            if "perception_snapshot_ref" in metadata:
                self.validate_ref(metadata["perception_snapshot_ref"], path + ".perception_snapshot_ref")
            self.primitive(metadata["engine"], "Text", path + ".engine")
            self.primitive(metadata["engine_version"], "Text", path + ".engine_version")
            self.validate_content(metadata["configuration_ref"], path + ".configuration_ref")
            for i, ref in enumerate(metadata["observation_refs"]):
                self.validate_content(ref, f"{path}.observation_refs[{i}]")
        elif kind == "NATIVE_BINDING":
            self.validate_ref(metadata["native_binding_ref"], path + ".native_binding_ref")
            self.validate_evaluator(metadata["evaluator_binding"], path + ".evaluator_binding")
            for i, ref in enumerate(metadata["observation_refs"]):
                self.validate_content(ref, f"{path}.observation_refs[{i}]")
            self.primitive(metadata["outcome"], "BindingStatus", path + ".outcome")
        elif kind == "DETERMINISTIC_EVALUATION":
            self.validate_ref(metadata["evaluation_ref"], path + ".evaluation_ref")
            self.validate_evaluator(metadata["evaluator_binding"], path + ".evaluator_binding")
            self.primitive(metadata["outcome"], "Text", path + ".outcome")
        elif kind == "AI_INTERACTION":
            self.validate_ref(metadata["ai_interaction_ref"], path + ".ai_interaction_ref")
            for field in ("provider", "model"):
                self.primitive(metadata[field], "Text", path + "." + field)
            if metadata["model_version"] is not None:
                self.primitive(metadata["model_version"], "Text", path + ".model_version")
            self.validate_content(metadata["instruction_ref"], path + ".instruction_ref")
            for i, ref in enumerate(metadata["context_refs"]):
                self.validate_content(ref, f"{path}.context_refs[{i}]")
            self.validate_content(metadata["output_ref"], path + ".output_ref")
        elif kind == "REPLAY":
            self.validate_ref(metadata["approved_change_set_ref"], path + ".approved_change_set_ref")
            if "execution_ref" in metadata:
                self.validate_ref(metadata["execution_ref"], path + ".execution_ref")
            self.primitive(metadata["engine"], "Text", path + ".engine")
            self.primitive(metadata["engine_version"], "Text", path + ".engine_version")
            self.validate_document_ref(metadata["input_document_version_ref"], path + ".input_document_version_ref")
            if metadata["output_document_version_ref"] is not None:
                self.validate_document_ref(metadata["output_document_version_ref"], path + ".output_document_version_ref")
        elif kind == "VALIDATION":
            self.validate_ref(metadata["validation_report_ref"], path + ".validation_report_ref")
            self.validate_actor(metadata["validator"], path + ".validator")
            if metadata["validator"].get("actor_type") != "VALIDATOR":
                self.error(path, "VALIDATION requires VALIDATOR")
            self.primitive(metadata["validator_version"], "Text", path + ".validator_version")
            self.validate_content(metadata["configuration_ref"], path + ".configuration_ref")
            self.validate_document_ref(metadata["input_document_version_ref"], path + ".input_document_version_ref")
            self.validate_document_ref(metadata["output_document_version_ref"], path + ".output_document_version_ref")
            for i, ref in enumerate(metadata["observation_refs"]):
                self.validate_content(ref, f"{path}.observation_refs[{i}]")
        elif kind == "EXCEPTION":
            self.validate_ref(metadata["exception_ref"], path + ".exception_ref")
            self.primitive(metadata["first_material_failure_event_id"], "ID", path + ".first_material_failure_event_id")
            for i, ref in enumerate(metadata["remediation_refs"]):
                self.validate_ref(ref, f"{path}.remediation_refs[{i}]")
        if "first_material_failure_event_id" in metadata:
            self.primitive(metadata["first_material_failure_event_id"], "ID", path + ".first_material_failure_event_id")

    def validate_events(self) -> None:
        events = self.data.get("audit_events", [])
        if not isinstance(events, list):
            self.error("$.audit_events", "must be an array")
            return
        roots, positions = [], {}
        for index, event in enumerate(events):
            path = f"$.audit_events[{index}]"
            if not isinstance(event, dict):
                self.error(path, "must be an object")
                continue
            positions[event.get("event_id")] = index
            event_schema = self.openapi.get("components", {}).get("schemas", {}).get("AuditEvent")
            if event_schema:
                validator = Draft202012Validator(event_schema, resolver=self.openapi_resolver)
                for issue in sorted(validator.iter_errors(event), key=lambda error: list(error.path)):
                    location = ".".join(str(part) for part in issue.path)
                    self.error(path + ("." + location if location else ""),
                               "OpenAPI schema: " + issue.message)
            for field, type_name in {
                "event_id": "ID", "event_version": "PositiveInt", "schema_version": "SchemaVersion",
                "event_type": "EventType", "occurred_at": "Timestamp", "task_id": "ID",
                "correlation_id": "ID",
            }.items():
                if field in event:
                    self.primitive(event[field], type_name, path + "." + field)
            self.validate_actor(event.get("actor"), path + ".actor")
            for i, ref in enumerate(event.get("document_version_refs", [])):
                self.validate_document_ref(ref, f"{path}.document_version_refs[{i}]")
            for i, target in enumerate(event.get("business_target_ids", [])):
                self.primitive(target, "BusinessTargetID", f"{path}.business_target_ids[{i}]")
            for field in ("object_refs", "input_refs", "output_refs"):
                for i, ref in enumerate(event.get(field, [])):
                    self.validate_ref(ref, f"{path}.{field}[{i}]")
            for i, code in enumerate(event.get("error_codes", [])):
                self.primitive(code, "ErrorCode", f"{path}.error_codes[{i}]")
            self.validate_metadata(event.get("metadata"), path + ".metadata")
            if event.get("causation_event_id") is None:
                roots.append(event)
            required_kind = EVENT_METADATA_KIND.get(event.get("event_type"))
            if required_kind and event.get("metadata", {}).get("metadata_kind") != required_kind:
                self.error(path, f"event requires {required_kind} metadata")
            allowed = EVENT_ACTOR_TYPES.get(event.get("event_type"))
            if allowed and event.get("actor", {}).get("actor_type") not in allowed:
                self.error(path, "actor type is not allowed")
            payload = dict(event)
            payload.pop("integrity_payload_hash", None)
            try:
                if event.get("integrity_payload_hash") != digest(payload):
                    self.error(path, "integrity_payload_hash mismatch")
            except Exception as exc:
                self.error(path, f"integrity hash failed: {exc}")
        if len(roots) != 1 or (roots and roots[0].get("event_type") != "TASK_CREATED"):
            self.error("$.audit_events", "exactly one TASK_CREATED root is required")
        event_by_id = {event.get("event_id"): event for event in events if isinstance(event, dict)}
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue
            cause = event.get("causation_event_id")
            if event.get("event_type") != "TASK_CREATED":
                if not cause or cause not in event_by_id:
                    self.error(f"$.audit_events[{index}]", "non-root event must have a cause")
                elif event_by_id[cause].get("task_id") != event.get("task_id"):
                    self.error(f"$.audit_events[{index}]", "cause crosses task boundary")
                elif positions.get(cause, index) >= index:
                    self.error(f"$.audit_events[{index}]", "cause must precede event")
        visiting, complete = set(), set()
        def visit(event_id: str) -> None:
            if event_id in complete or event_id not in event_by_id:
                return
            if event_id in visiting:
                self.error("$.audit_events", "causation cycle")
                return
            visiting.add(event_id)
            cause = event_by_id[event_id].get("causation_event_id")
            if cause:
                visit(cause)
            visiting.remove(event_id)
            complete.add(event_id)
        for event_id in event_by_id:
            visit(event_id)

    def validate_material_coverage(self) -> None:
        for record_type, event_type in MATERIAL_EVENT_MAP.items():
            for key, record in self.records.items():
                if key[0] != record_type:
                    continue
                if not any(event.get("event_type") == event_type and any(
                    ref.get("object_type") == record_type
                    and ref.get("object_id") == record.get("id")
                    and ref.get("revision") == record.get("revision")
                    for ref in event.get("output_refs", [])
                ) for event in self.data.get("audit_events", [])):
                    self.error(f"$.records[{record_type}:{record.get('id')}]", "missing material event")
        for record_type in ("RuleEvaluation", "SourceAssessment", "EvidenceCheck", "EvidenceAssessment"):
            for key, record in self.records.items():
                if key[0] != record_type:
                    continue
                ref = {"object_type": record_type, "object_id": record.get("id"), "revision": record.get("revision")}
                matches = [event for event in self.data.get("audit_events", [])
                           if event.get("event_type") == MATERIAL_EVENT_MAP[record_type]
                           and event.get("metadata", {}).get("evaluation_ref") == ref]
                if matches and matches[0].get("metadata", {}).get("evaluator_binding") != record.get("evaluator_binding"):
                    self.error(f"$.records[{record_type}:{record.get('id')}]", "evaluator binding mismatch")

    def validate_replay_and_governance(self) -> None:
        records_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (typ, _rid, _revision), record in self.records.items():
            records_by_type[typ].append(record)
        task_records = sorted(records_by_type["FoundationTask"], key=lambda r: r.get("revision", 0))
        for typ, records in records_by_type.items():
            by_id: dict[str, list[int]] = defaultdict(list)
            for record in records:
                by_id[record.get("id")].append(record.get("revision"))
            for rid, revisions in by_id.items():
                if sorted(revisions) != list(range(1, max(revisions) + 1)):
                    self.error(f"$.records[{typ}:{rid}]", "revisions are not contiguous")
        lifecycle_edges = {
            "DocumentArtifact": {"REGISTERED": {"PREFLIGHTING", "REJECTED"}, "PREFLIGHTING": {"READY", "BLOCKED", "REJECTED"}, "READY": {"BLOCKED", "SUPERSEDED"}, "BLOCKED": {"PREFLIGHTING", "SUPERSEDED", "REJECTED"}, "STAGED": {"RELEASED", "QUARANTINED"}, "QUARANTINED": {"STAGED", "SUPERSEDED"}, "RELEASED": {"QUARANTINED", "SUPERSEDED"}},
            "DocumentPreflightAssessment": {"PENDING": {"ASSESSING", "SUPERSEDED"}, "ASSESSING": {"COMPLETED", "FAILED", "SUPERSEDED"}, "COMPLETED": {"SUPERSEDED"}},
            "SourceAssessment": {"PENDING": {"ASSESSING", "SUPERSEDED"}, "ASSESSING": {"COMPLETED", "FAILED", "SUPERSEDED"}, "COMPLETED": {"SUPERSEDED"}},
            "MappingProposal": {"PROPOSED": {"UNDER_REVIEW", "BLOCKED", "SUPERSEDED"}, "UNDER_REVIEW": {"ACCEPTED", "BLOCKED", "REJECTED", "SUPERSEDED"}, "BLOCKED": {"UNDER_REVIEW", "REJECTED", "SUPERSEDED"}, "ACCEPTED": {"SUPERSEDED"}},
            "ChangeProposal": {"DRAFT": {"READY_FOR_REVIEW", "BLOCKED", "SUPERSEDED"}, "BLOCKED": {"READY_FOR_REVIEW", "SUPERSEDED"}, "READY_FOR_REVIEW": {"IN_REVIEW", "BLOCKED", "SUPERSEDED"}, "IN_REVIEW": {"APPROVED", "REJECTED", "BLOCKED", "SUPERSEDED"}, "APPROVED": {"SUPERSEDED"}},
            "ApprovedChangeSet": {"APPROVED": {"INVALIDATED", "REVOKED", "SUPERSEDED"}},
            "ExecutionResult": {"QUEUED": {"PREFLIGHTING", "CANCELLED"}, "PREFLIGHTING": {"RUNNING", "REFUSED", "CANCELLED"}, "RUNNING": {"SUCCEEDED", "FAILED"}},
            "ValidationReport": {"PENDING": {"RUNNING", "CANCELLED"}, "RUNNING": {"PASSED", "FAILED", "INCONCLUSIVE", "CANCELLED"}},
            "ExceptionRecord": {"OPEN": {"ACKNOWLEDGED", "REMEDIATION_PENDING"}, "ACKNOWLEDGED": {"REMEDIATION_PENDING"}, "REMEDIATION_PENDING": {"RESOLVED", "OPEN"}, "RESOLVED": {"CLOSED", "OPEN"}},
        }
        for typ, edges in lifecycle_edges.items():
            by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for record in records_by_type[typ]:
                by_id[record.get("id")].append(record)
            for rid, revisions in by_id.items():
                revisions.sort(key=lambda r: r.get("revision", 0))
                for before, after in zip(revisions, revisions[1:]):
                    if before.get("status") != after.get("status") and after.get("status") not in edges.get(before.get("status"), set()):
                        self.error(f"$.records[{typ}:{rid}]", f"illegal transition {before.get('status')} -> {after.get('status')}")
        for i in range(1, len(task_records)):
            before, after = task_records[i - 1].get("status"), task_records[i].get("status")
            if before != after and after not in TASK_EDGES.get(before, set()):
                self.error("$.records.FoundationTask", f"illegal transition {before} -> {after}")
        acs_records = records_by_type["ApprovedChangeSet"]
        for acs in acs_records:
            authorization = acs.get("authorization", {})
            if acs.get("authorization_digest") != digest(authorization):
                self.error(f"$.records[ApprovedChangeSet:{acs.get('id')}]", "authorization_digest mismatch")
            if acs.get("status") == "APPROVED":
                for ref in authorization.get("source_assessment_refs", []):
                    record = self.records.get((ref.get("object_type"), ref.get("object_id"), ref.get("revision")))
                    if not record or record.get("status") != "COMPLETED" or record.get("outcome") != "SUFFICIENT":
                        self.error(f"$.records[ApprovedChangeSet:{acs.get('id')}]", "insufficient source")
                for ref in authorization.get("evidence_assessment_refs", []):
                    record = self.records.get((ref.get("object_type"), ref.get("object_id"), ref.get("revision")))
                    if not record or record.get("status") != "VERIFIED":
                        self.error(f"$.records[ApprovedChangeSet:{acs.get('id')}]", "unverified evidence")
                for ref in authorization.get("review_decision_refs", []):
                    record = self.records.get((ref.get("object_type"), ref.get("object_id"), ref.get("revision")))
                    if not record or record.get("outcome") != "APPROVE":
                        self.error(f"$.records[ApprovedChangeSet:{acs.get('id')}]", "approval missing")
                if authorization.get("mutation_profile") != "TRANSITIONAL":
                    self.error(f"$.records[ApprovedChangeSet:{acs.get('id')}]", "mutation profile is not qualified")
            for change in authorization.get("approved_changes", []):
                payload_kind = change.get("payload", {}).get("kind")
                expected_payload = {
                    "REPLACE_RUN_TEXT": "RUN_TEXT_REPLACEMENT",
                    "REPLACE_SDT_TEXT": "SDT_TEXT_REPLACEMENT",
                    "REPLACE_SIMPLE_TABLE_CELL_TEXT": "SIMPLE_TABLE_CELL_TEXT_REPLACEMENT",
                }.get(change.get("operation"))
                if expected_payload and payload_kind != expected_payload:
                    self.error("$.records.ApprovedChangeSet", "operation/payload mismatch")
                ref = change.get("native_locator_ref", {})
                locator = self.records.get((ref.get("object_type"), ref.get("object_id"), ref.get("revision")))
                if locator and locator.get("document_version_ref") != authorization.get("target_document_version_ref"):
                    self.error("$.records.ApprovedChangeSet", "locator not bound to target hash")
                compatible_locator = {
                    "REPLACE_RUN_TEXT": {"DOCX_RUN"},
                    "REPLACE_SDT_TEXT": {"DOCX_CONTENT_CONTROL"},
                    "REPLACE_SIMPLE_TABLE_CELL_TEXT": {"DOCX_TABLE_CELL"},
                }.get(change.get("operation"))
                if locator and compatible_locator and locator.get("locator_type") not in compatible_locator:
                    self.error("$.records.ApprovedChangeSet", "operation has no compatible exact locator")
                if "fuzzy" in json.dumps(change, sort_keys=True).lower():
                    self.error("$.records.ApprovedChangeSet", "fuzzy locator semantics are forbidden")
        for index, action in enumerate(self.data.get("actions", []) or []):
            observations = action.get("observations", {}) if isinstance(action, dict) else {}
            if observations.get("fuzzy_fallback_attempted") is not False:
                self.error(f"$.actions[{index}]", "fuzzy fallback must be explicitly false")
            if action.get("locator_override") is not None or action.get("operation_override") is not None or action.get("payload_override") is not None:
                self.error(f"$.actions[{index}]", "free-form or fuzzy execution override is forbidden")
        requests = []
        for index, action in enumerate(self.data.get("actions", []) or []):
            request = action.get("replay_request") if isinstance(action, dict) else None
            if request is None:
                continue
            requests.append(request)
            if set(request) != {"execution_id", "approved_change_set_ref"}:
                self.error(f"$.actions[{index}].replay_request", "ReplayRequest has extra or missing fields")
            self.validate_ref(request.get("approved_change_set_ref"), f"$.actions[{index}].replay_request.approved_change_set_ref")
        if requests and not acs_records:
            self.error("$.actions", "ReplayRequest without authorization")
        for record in records_by_type["AIInteractionRecord"]:
            if "execution_authority" in record or record.get("actor", {}).get("actor_type") != "AI":
                self.error("$.records.AIInteractionRecord", "AI has execution authority or wrong actor")
        for execution in records_by_type["ExecutionResult"]:
            if execution.get("status") == "REFUSED" and "output_document_version_ref" in execution:
                self.error("$.records.ExecutionResult", "refused execution has output")
            auth_ref = execution.get("approved_change_set_ref")
            if isinstance(auth_ref, dict):
                auth_record = self.records.get((auth_ref.get("object_type"), auth_ref.get("object_id"), auth_ref.get("revision")))
                if auth_record:
                    target = auth_record.get("authorization", {}).get("target_document_version_ref")
                    input_ref = execution.get("input_document_version_ref")
                    if execution.get("status") != "REFUSED" and input_ref != target:
                        self.error("$.records.ExecutionResult", "execution input is not authorization-locked")
                    if execution.get("status") == "REFUSED" and "STALE_DOCUMENT_VERSION" not in execution.get("error_codes", []) and input_ref != target:
                        self.error("$.records.ExecutionResult", "refused execution input mismatch lacks stale error")
        for report in records_by_type["ValidationReport"]:
            if report.get("validator", {}).get("actor_type") != "VALIDATOR":
                self.error("$.records.ValidationReport", "validator is not independent")
        for preflight in records_by_type["DocumentPreflightAssessment"]:
            if preflight.get("detected_conformance") == "STRICT" and any(
                result.get("status") == "UNSUPPORTED" for result in preflight.get("capability_results", [])
            ) and (acs_records or requests or records_by_type["ExecutionResult"]):
                self.error("$.records.DocumentPreflightAssessment", "Strict OOXML bypassed refusal")

    def compare_expected(self) -> None:
        expected = self.data.get("expected", {})
        tasks = sorted([r for r in self.records.values() if r.get("object_type") == "FoundationTask"],
                       key=lambda item: item.get("revision", 0))
        last_task = tasks[-1] if tasks else {}
        task_ref = {"object_type": "FoundationTask", "object_id": last_task.get("id"), "revision": last_task.get("revision")} if last_task else None
        if expected.get("task_ref") != task_ref:
            self.error("$.expected.task_ref", "does not match latest task revision")
        if expected.get("task_status") != last_task.get("status"):
            self.error("$.expected.task_status", "does not match derived status")
        if expected.get("release_status") != last_task.get("release_status"):
            self.error("$.expected.release_status", "does not match derived release")
        first_error = next((event for event in self.data.get("audit_events", []) if event.get("error_codes")), None)
        if expected.get("first_material_failure_event_id") != (first_error.get("event_id") if first_error else None):
            self.error("$.expected.first_material_failure_event_id", "does not match first error event")
        if expected.get("ai_execution_authority") is not False or expected.get("fuzzy_fallback_attempted") is not False:
            self.error("$.expected", "authority and fuzzy assertions must be false")
        actual_mutation = any(record.get("status") in {"SUCCEEDED", "FAILED"}
                              for key, record in self.records.items() if key[0] == "ExecutionResult")
        if expected.get("mutation_attempted") != actual_mutation:
            self.error("$.expected.mutation_attempted", "does not match execution outcome")
        latest_acs: dict[str, int] = {}
        for key, record in self.records.items():
            if key[0] == "ApprovedChangeSet":
                latest_acs[record["id"]] = max(latest_acs.get(record["id"], 0), record["revision"])
        actual_acs = [{"object_type": "ApprovedChangeSet", "object_id": rid, "revision": revision}
                      for rid, revision in sorted(latest_acs.items())]
        if expected.get("approved_change_set_refs") != actual_acs:
            self.error("$.expected.approved_change_set_refs", "does not match authorization revisions")
        actual_exec = [{"object_type": "ExecutionResult", "object_id": record["id"], "revision": record["revision"]}
                       for key, record in sorted(self.records.items()) if key[0] == "ExecutionResult"]
        if expected.get("execution_refs") != actual_exec:
            self.error("$.expected.execution_refs", "does not match executions")
        actual_validation = [{"object_type": "ValidationReport", "object_id": record["id"], "revision": record["revision"]}
                             for key, record in sorted(self.records.items()) if key[0] == "ValidationReport"]
        if expected.get("validation_report_refs") != actual_validation:
            self.error("$.expected.validation_report_refs", "does not match validation reports")
        last_error = next((event for event in reversed(self.data.get("audit_events", [])) if event.get("error_codes")), None)
        actual_errors = last_error.get("error_codes", []) if last_error else []
        if expected.get("error_codes") != actual_errors:
            self.error("$.expected.error_codes", "does not match final material error event")
        expected_targets = expected.get("targets", [])
        for item in expected_targets:
            ref = item.get("target_region_ref", {})
            region = self.records.get((ref.get("object_type"), ref.get("object_id"), ref.get("revision")))
            if not region:
                self.error("$.expected.targets", "target_region_ref does not resolve")
                continue
            if region.get("business_target_id") != item.get("business_target_id") or region.get("verification_status") != item.get("verification_status"):
                self.error("$.expected.targets", "target projection does not match region")
        output_ref = expected.get("output_document_ref")
        if output_ref:
            output = self.records.get((output_ref.get("object_type"), output_ref.get("object_id"), output_ref.get("revision")))
            if not output:
                self.error("$.expected.output_document_ref", "does not resolve")
            elif output.get("status") != expected.get("output_document_status"):
                self.error("$.expected.output_document_status", "does not match document status")
        for ref in expected.get("preserved_record_refs", []):
            if not isinstance(ref, dict) or (ref.get("object_type"), ref.get("object_id"), ref.get("revision")) not in self.records:
                self.error("$.expected.preserved_record_refs", "does not resolve")
        if expected.get("new_correlation_id") is not None and not any(
            event.get("correlation_id") == expected.get("new_correlation_id") for event in self.data.get("audit_events", [])
        ):
            self.error("$.expected.new_correlation_id", "does not occur in audit events")

    def run(self) -> dict[str, Any]:
        self.load()
        if not self.errors:
            self.validate_records()
            self.validate_events()
            self.validate_material_coverage()
            self.validate_replay_and_governance()
            self.compare_expected()
        status = "PASS" if not self.errors else "FAIL"
        return {
            "scenario": self.scenario, "schema_result": status,
            "reference_result": status, "state_machine_result": status,
            "governance_result": status, "hash_result": status,
            "overall_result": status, "error_count": len(self.errors),
            "errors": self.errors,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    global CONTRACTS, EXAMPLES
    CONTRACTS, EXAMPLES = args.root / "docs" / "contracts", args.root / "docs" / "contracts" / "examples"
    enums, openapi = enum_registry(), load_openapi_contract()
    results = [FixtureValidator(path, enums, openapi).run() for path in sorted(EXAMPLES.glob("*.yaml"))]
    report = {
        "schema_version": SCHEMA_VERSION,
        "validator": "foundation-contract-fixture-validator",
        "scenarios": results,
        "overall_result": "PASS" if len(results) == 8 and all(x["overall_result"] == "PASS" for x in results) else "FAIL",
    }
    encoded = json.dumps(report, indent=2, sort_keys=True)
    print(encoded)
    if args.report:
        args.report.write_text(encoded + "\n", encoding="utf-8")
    return 0 if report["overall_result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

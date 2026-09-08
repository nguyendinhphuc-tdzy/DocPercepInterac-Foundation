from __future__ import annotations

from enum import StrEnum
import inspect

from foundation.domain import DOMAIN_RECORD_MODELS, ObjectType
from foundation.domain import enums as domain_enums


BASE_REQUIRED = {"schema_version", "object_type", "id", "revision", "created_at"}
TASK_OWNED_EXCEPTIONS = {
    ObjectType.FOUNDATION_TASK,
    ObjectType.TARGET_CONTRACT_DEFINITION,
    ObjectType.TARGET_REGION_DEFINITION,
    ObjectType.RULE_PACK,
    ObjectType.BUSINESS_RULE,
    ObjectType.FRESHNESS_POLICY,
    ObjectType.SOURCE_REQUIREMENT,
    ObjectType.VALIDATION_PLAN,
    ObjectType.AUDIT_EVENT,
}


def _component_fields(component: dict[str, object]) -> tuple[set[str], set[str]]:
    properties: set[str] = set()
    required: set[str] = set()
    for branch in [component, *component.get("allOf", [])]:
        if "$ref" in branch:
            continue
        properties.update(branch.get("properties", {}))
        required.update(branch.get("required", []))
    return properties, required


def test_registry_exactly_projects_openapi_object_types(openapi_document):
    schema_values = set(
        openapi_document["components"]["schemas"]["ObjectType"]["enum"]
    )
    assert {key.value for key in DOMAIN_RECORD_MODELS} == schema_values


def test_python_enum_values_are_projected_by_openapi(openapi_document):
    projected: set[str] = set()

    def visit(value):
        if isinstance(value, dict):
            projected.update(str(item) for item in value.get("enum", []))
            if "const" in value:
                projected.add(str(value["const"]))
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(openapi_document["components"]["schemas"])
    python_values = {
        member.value
        for _, enum_type in inspect.getmembers(domain_enums, inspect.isclass)
        if issubclass(enum_type, StrEnum) and enum_type is not StrEnum
        for member in enum_type
    }
    assert python_values <= projected
    assert set(openapi_document["components"]["schemas"]["ErrorCode"]["enum"]) <= python_values
    assert set(openapi_document["components"]["schemas"]["EventType"]["enum"]) <= python_values


def test_model_fields_and_requiredness_track_openapi_components(openapi_document):
    schemas = openapi_document["components"]["schemas"]
    envelope_properties = set(schemas["RecordEnvelope"]["properties"])
    for object_type, model in DOMAIN_RECORD_MODELS.items():
        component_properties, component_required = _component_fields(
            schemas[object_type.value]
        )
        if object_type is ObjectType.AUDIT_EVENT:
            expected_properties = component_properties
            expected_required = component_required
        else:
            expected_properties = component_properties | envelope_properties
            expected_required = component_required | BASE_REQUIRED
            if object_type not in TASK_OWNED_EXCEPTIONS:
                expected_required.add("task_id")
            else:
                expected_properties.discard("task_id")
        assert set(model.model_fields) == expected_properties, object_type
        actual_required = {
            name for name, field in model.model_fields.items() if field.is_required()
        }
        assert actual_required == expected_required, object_type


def test_openapi_closed_components_remain_closed(openapi_document):
    schemas = openapi_document["components"]["schemas"]
    for object_type in ObjectType:
        schema = schemas[object_type.value]
        if object_type is ObjectType.AUDIT_EVENT:
            assert schema.get("additionalProperties") is False
        else:
            assert schema.get("unevaluatedProperties") is False

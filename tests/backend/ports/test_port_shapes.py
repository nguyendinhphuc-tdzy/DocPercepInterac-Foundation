from __future__ import annotations

from inspect import isclass

from foundation.ports import (
    AIInterpretationPort,
    AuditRepository,
    DomainRecordRepository,
    NativeIdentityPort,
    NativeIdentityResult,
    PerceptionPort,
    PerceptionResult,
    ReplayPort,
    ValidationPort,
)


def test_v2_ports_are_interfaces_without_runtime_adapters():
    ports = [PerceptionPort, NativeIdentityPort, AIInterpretationPort, ReplayPort, ValidationPort, DomainRecordRepository, AuditRepository]
    assert all(isclass(port) and getattr(port, "_is_protocol", False) for port in ports)


def test_perception_and_native_results_are_explicit_non_contract_dtos():
    assert isclass(PerceptionResult)
    assert isclass(NativeIdentityResult)
    assert set(PerceptionResult.__dataclass_fields__) == {"snapshot", "semantic_objects"}
    assert set(NativeIdentityResult.__dataclass_fields__) == {
        "preflight_assessment",
        "native_locators",
        "native_bindings",
    }

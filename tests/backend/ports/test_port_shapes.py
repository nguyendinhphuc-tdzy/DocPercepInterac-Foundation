from __future__ import annotations

from inspect import isclass

from foundation.ports import (
    AIInterpretationPort,
    AuditRepository,
    DomainRecordRepository,
    NativeIdentityPort,
    PerceptionPort,
    ReplayPort,
    ValidationPort,
)


def test_v2_ports_are_interfaces_without_runtime_adapters():
    ports = [PerceptionPort, NativeIdentityPort, AIInterpretationPort, ReplayPort, ValidationPort, DomainRecordRepository, AuditRepository]
    assert all(isclass(port) and getattr(port, "_is_protocol", False) for port in ports)

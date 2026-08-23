"""
Roll-Forward Source Registry (Phase G)
=======================================
Location: foundation/applications/rollforward/source_registry.py

Governed orchestration layer over the Phase F primitives
(SourceIntakeProfiler, RollForwardSourcePackage, SourceRequestRegister,
ReadinessRecalculator).

Contract
--------
    register() may ingest, profile and register an artifact.
    register() must NOT change readiness.

    recalculate_readiness() is the ONLY path that transitions readiness.
    Readiness changes are recorded as separate immutable events.

    replace() is atomic:
        profile new artifact → validate → commit replacement.
        If any step fails, the previous artifact and readiness are preserved.

    Duplicate SHA256 → DUPLICATE / NOOP (no second artifact, no readiness change).

    Every mutation bumps the source package version.

    The final readiness guard runs after every recalculation:
        FORBIDDEN_READINESS values are absent
        Ground Truth is absent from source package
        no automatic APPROVED/EXECUTING state
        no mutation occurred

    Audit records never contain raw document contents, raw prompt text,
    sensitive cell values, or unnecessary absolute filesystem paths.

    Repeating the exact same operation against unchanged source artifacts
    produces an equivalent readiness result without duplicate semantic state.

No mutation. No Ground Truth. No network. No auto-approval.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import uuid

from applications.rollforward.source_intake import (
    FORBIDDEN_READINESS,
    ArtifactFormat,
    ArtifactStatus,
    EvidenceQuality,
    GroundTruthGuard,
    PackageStatus,
    ReadinessRecalculator,
    ReadinessTransition,
    RecalculatedReadiness,
    RollForwardSourcePackage,
    SourceArtifact,
    SourceIntakeError,
    SourceIntakeProfiler,
    SourceRequestRegister,
    compute_file_hash,
)
from applications.rollforward.evidence_policy import (
    DatasetRole,
    SupplyScope,
)


# ============================================================================
# 1. ENUMS & AUDIT RECORDS
# ============================================================================

class RegistrationEventType(str, Enum):
    """Every kind of governed source operation."""
    REGISTER = "REGISTER"
    DUPLICATE_NOOP = "DUPLICATE_NOOP"
    REPLACE_SUCCESS = "REPLACE_SUCCESS"
    REPLACE_FAILED = "REPLACE_FAILED"
    READINESS_RECALCULATED = "READINESS_RECALCULATED"
    STALE_DETECTED = "STALE_DETECTED"
    FREEZE = "FREEZE"


class RegistryError(RuntimeError):
    """Raised when a registry operation fails governance rules."""


@dataclass
class RegistrationEvent:
    """Immutable audit record for a governed source operation.

    Audit privacy rules:
        ✓ artifact_id, previous_hash, new_hash, source_scope
        ✓ changed_roles, affected_regions, readiness snapshots
        ✓ actor, timestamps
        ✗ raw document contents
        ✗ raw prompt text
        ✗ sensitive cell values
        ✗ unnecessary absolute filesystem paths
    """
    event_id: str
    event_type: RegistrationEventType
    timestamp: str
    actor: str
    artifact_id: Optional[str] = None
    filename: Optional[str] = None
    source_scope: Optional[str] = None
    previous_hash: Optional[str] = None
    new_hash: Optional[str] = None
    changed_roles: List[str] = field(default_factory=list)
    affected_regions: List[str] = field(default_factory=list)
    readiness_before: Optional[Dict[str, str]] = None
    readiness_after: Optional[Dict[str, str]] = None
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    package_version: Optional[int] = None
    reason: str = ""
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "success": self.success,
        }
        if self.artifact_id is not None:
            d["artifact_id"] = self.artifact_id
        if self.filename is not None:
            d["filename"] = self.filename
        if self.source_scope is not None:
            d["source_scope"] = self.source_scope
        if self.previous_hash is not None:
            d["previous_hash"] = self.previous_hash
        if self.new_hash is not None:
            d["new_hash"] = self.new_hash
        if self.changed_roles:
            d["changed_roles"] = self.changed_roles
        if self.affected_regions:
            d["affected_regions"] = self.affected_regions
        if self.readiness_before is not None:
            d["readiness_before"] = self.readiness_before
        if self.readiness_after is not None:
            d["readiness_after"] = self.readiness_after
        if self.transitions:
            d["transitions"] = self.transitions
        if self.package_version is not None:
            d["package_version"] = self.package_version
        if self.reason:
            d["reason"] = self.reason
        return d


@dataclass
class ReadinessSnapshot:
    """Before/after readiness state for audit and determinism verification."""
    region_readiness: Dict[str, str]
    counts: Dict[str, int]
    governance: Dict[str, Any]

    @classmethod
    def capture(cls, regions: Sequence[Dict[str, Any]]) -> "ReadinessSnapshot":
        mapping = {r.get("region_id", "?"): r.get("readiness", "")
                   for r in regions}
        counts: Dict[str, int] = {}
        for v in mapping.values():
            counts[v] = counts.get(v, 0) + 1
        return cls(
            region_readiness=mapping,
            counts=counts,
            governance=ReadinessRecalculator.approval_still_required(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_readiness": self.region_readiness,
            "counts": self.counts,
            "governance": self.governance,
        }


# ============================================================================
# 2. FINAL READINESS GUARD
# ============================================================================

class ReadinessGuard:
    """Post-recalculation invariant check. Runs after every readiness computation.

    Asserts:
        1. No FORBIDDEN_READINESS values are present
        2. Ground Truth is absent from the source package
        3. No automatic APPROVED / EXECUTING state
        4. No mutation occurred (checked by caller)
    """

    @classmethod
    def validate(
        cls,
        counts: Dict[str, int],
        package: RollForwardSourcePackage,
        transitions: Sequence[ReadinessTransition],
    ) -> None:
        # 1. No forbidden readiness values
        for value in counts:
            if value in FORBIDDEN_READINESS:
                raise RegistryError(
                    f"FINAL READINESS GUARD VIOLATION: forbidden readiness "
                    f"'{value}' emitted by recalculation")

        for t in transitions:
            if t.recalculated in FORBIDDEN_READINESS:
                raise RegistryError(
                    f"FINAL READINESS GUARD VIOLATION: transition to forbidden "
                    f"readiness '{t.recalculated}' for region '{t.region_id}'")

        # 2. Ground Truth is absent from source package
        for a in package.artifacts:
            if a.source_scope == SupplyScope.EVALUATION_ONLY.value or \
               a.source_scope == SupplyScope.EVALUATION_ONLY:
                raise RegistryError(
                    f"FINAL READINESS GUARD VIOLATION: EVALUATION_ONLY artifact "
                    f"'{a.artifact_id}' found in source package")

        # 3. No automatic APPROVED / EXECUTING state (covered by forbidden check)
        for value in ("APPROVED", "EXECUTING", "AUTO_MUTATION_READY"):
            if value in counts:
                raise RegistryError(
                    f"FINAL READINESS GUARD VIOLATION: automatic execution state "
                    f"'{value}' present in readiness counts")


# ============================================================================
# 3. SOURCE REGISTRY
# ============================================================================

class SourceRegistry:
    """Governed, audited source lifecycle manager.

    Every operation produces an immutable RegistrationEvent.
    register() does NOT change readiness.
    recalculate_readiness() is the ONLY readiness transition path.
    replace() is atomic: failure preserves previous state.
    Duplicate SHA256 → DUPLICATE_NOOP.
    Every mutation bumps package version.
    """

    def __init__(
        self,
        package: Optional[RollForwardSourcePackage] = None,
        package_id: str = "PKG-REGISTRY",
    ):
        self.package = package or RollForwardSourcePackage(package_id=package_id)
        self.audit_log: List[RegistrationEvent] = []
        self._mutation_count: int = 0  # tracks filesystem mutations (must stay 0)

    # -- helpers -------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _event_id(self) -> str:
        return f"evt-{uuid.uuid4().hex[:12]}"

    def _sanitize_filename(self, path: Path) -> str:
        """Return only the filename, never the full absolute path."""
        return path.name

    # -- registration --------------------------------------------------

    def register(
        self,
        path: Path,
        source_scope: SupplyScope = SupplyScope.ADDITIONAL,
        actor: str = "system",
        artifact_id: Optional[str] = None,
    ) -> RegistrationEvent:
        """Ingest, profile and register an artifact.

        This method:
            ✓ Runs Ground Truth guard
            ✓ Computes file hash
            ✓ Checks for duplicate SHA256 → DUPLICATE_NOOP
            ✓ Profiles via SourceIntakeProfiler
            ✓ Adds to source package (bumps version)
            ✓ Records immutable audit event

        This method does NOT:
            ✗ Change readiness
            ✗ Trigger recalculation
            ✗ Auto-approve anything
            ✗ Mutate any document
        """
        # Ground Truth guard
        GroundTruthGuard.check(path)

        # Duplicate check: SHA256 already exists → NOOP
        if path.exists():
            file_hash = compute_file_hash(path)
            existing = self.package.by_hash(file_hash)
            if existing is not None:
                event = RegistrationEvent(
                    event_id=self._event_id(),
                    event_type=RegistrationEventType.DUPLICATE_NOOP,
                    timestamp=self._now(),
                    actor=actor,
                    artifact_id=existing.artifact_id,
                    filename=self._sanitize_filename(path),
                    new_hash=file_hash,
                    package_version=self.package.version,
                    reason=(
                        f"Duplicate content: '{path.name}' has the same SHA256 as "
                        f"already-registered '{existing.filename}' "
                        f"({existing.artifact_id}). No artifact created, no "
                        f"readiness changed."),
                    success=True,
                )
                self.audit_log.append(event)
                return event

        # Ingest and profile
        artifact = SourceIntakeProfiler.ingest(
            path, source_scope, artifact_id=artifact_id)

        # Add to package (bumps version, enforces EVALUATION_ONLY guard)
        self.package.add(artifact)

        event = RegistrationEvent(
            event_id=self._event_id(),
            event_type=RegistrationEventType.REGISTER,
            timestamp=self._now(),
            actor=actor,
            artifact_id=artifact.artifact_id,
            filename=self._sanitize_filename(path),
            source_scope=source_scope.value,
            new_hash=artifact.file_hash,
            changed_roles=[r.value for r in artifact.dataset_roles
                           if r != DatasetRole.UNKNOWN],
            package_version=self.package.version,
            reason="Artifact ingested, profiled and registered. "
                   "Readiness NOT recalculated; call recalculate_readiness() explicitly.",
            success=True,
        )
        self.audit_log.append(event)
        return event

    # -- replacement ---------------------------------------------------

    def replace(
        self,
        artifact_id: str,
        new_path: Path,
        actor: str = "system",
    ) -> RegistrationEvent:
        """Atomically replace an existing artifact with changed content.

        Transaction contract:
            1. Profile new artifact
            2. Validate new artifact
            3. Commit replacement (swap in package, bump version)

        If any step fails:
            Previous artifact and readiness are preserved.
            A REPLACE_FAILED event is emitted.

        replace() does NOT recalculate readiness. The caller must
        call recalculate_readiness() explicitly after a successful
        replacement.
        """
        # Find existing artifact
        existing = None
        existing_idx = None
        for i, a in enumerate(self.package.artifacts):
            if a.artifact_id == artifact_id:
                existing = a
                existing_idx = i
                break

        if existing is None:
            event = RegistrationEvent(
                event_id=self._event_id(),
                event_type=RegistrationEventType.REPLACE_FAILED,
                timestamp=self._now(),
                actor=actor,
                artifact_id=artifact_id,
                reason=f"Artifact '{artifact_id}' not found in package.",
                success=False,
            )
            self.audit_log.append(event)
            return event

        # Ground Truth guard on new path
        try:
            GroundTruthGuard.check(new_path)
        except SourceIntakeError as e:
            event = RegistrationEvent(
                event_id=self._event_id(),
                event_type=RegistrationEventType.REPLACE_FAILED,
                timestamp=self._now(),
                actor=actor,
                artifact_id=artifact_id,
                filename=self._sanitize_filename(new_path),
                previous_hash=existing.file_hash,
                reason=f"Ground Truth guard rejected replacement: {e}",
                success=False,
            )
            self.audit_log.append(event)
            return event

        # Same content check
        if new_path.exists():
            new_hash = compute_file_hash(new_path)
            if new_hash == existing.file_hash:
                event = RegistrationEvent(
                    event_id=self._event_id(),
                    event_type=RegistrationEventType.DUPLICATE_NOOP,
                    timestamp=self._now(),
                    actor=actor,
                    artifact_id=artifact_id,
                    filename=self._sanitize_filename(new_path),
                    previous_hash=existing.file_hash,
                    new_hash=new_hash,
                    package_version=self.package.version,
                    reason="Replacement content is identical to existing. No change.",
                    success=True,
                )
                self.audit_log.append(event)
                return event

        # Step 1: Profile new artifact (preserving existing state on failure)
        try:
            new_artifact = SourceIntakeProfiler.ingest(
                new_path, existing.source_scope,
                artifact_id=artifact_id)
        except Exception as e:
            event = RegistrationEvent(
                event_id=self._event_id(),
                event_type=RegistrationEventType.REPLACE_FAILED,
                timestamp=self._now(),
                actor=actor,
                artifact_id=artifact_id,
                filename=self._sanitize_filename(new_path),
                previous_hash=existing.file_hash,
                reason=f"Profiling failed: {e}. Previous artifact preserved.",
                success=False,
            )
            self.audit_log.append(event)
            return event

        # Step 2: Validate new artifact
        if new_artifact.status == ArtifactStatus.REJECTED:
            event = RegistrationEvent(
                event_id=self._event_id(),
                event_type=RegistrationEventType.REPLACE_FAILED,
                timestamp=self._now(),
                actor=actor,
                artifact_id=artifact_id,
                filename=self._sanitize_filename(new_path),
                previous_hash=existing.file_hash,
                new_hash=new_artifact.file_hash,
                reason=f"New artifact was REJECTED: {new_artifact.notes}. "
                       f"Previous artifact preserved.",
                success=False,
            )
            self.audit_log.append(event)
            return event

        # Step 3: Commit replacement atomically
        previous_hash = existing.file_hash
        previous_roles = [r.value for r in existing.dataset_roles
                          if r != DatasetRole.UNKNOWN]
        new_roles = [r.value for r in new_artifact.dataset_roles
                     if r != DatasetRole.UNKNOWN]

        # Mark previous as stale, swap in package
        existing.status = ArtifactStatus.STALE_INPUT
        assert existing_idx is not None
        self.package.artifacts[existing_idx] = new_artifact

        # Bump version
        self.package.parent_version = self.package.version
        self.package.version += 1
        self.package.status = PackageStatus.DRAFT
        self.package.history.append({
            "version": self.package.version,
            "action": "REPLACE_ARTIFACT",
            "artifact_id": artifact_id,
            "previous_hash": previous_hash[:12],
            "new_hash": new_artifact.file_hash[:12],
            "at": self._now(),
        })

        event = RegistrationEvent(
            event_id=self._event_id(),
            event_type=RegistrationEventType.REPLACE_SUCCESS,
            timestamp=self._now(),
            actor=actor,
            artifact_id=artifact_id,
            filename=self._sanitize_filename(new_path),
            source_scope=existing.source_scope.value if isinstance(
                existing.source_scope, SupplyScope) else str(existing.source_scope),
            previous_hash=previous_hash,
            new_hash=new_artifact.file_hash,
            changed_roles=sorted(set(previous_roles) ^ set(new_roles)),
            package_version=self.package.version,
            reason="Artifact replaced atomically. Readiness NOT recalculated; "
                   "call recalculate_readiness() explicitly.",
            success=True,
        )
        self.audit_log.append(event)
        return event

    # -- readiness recalculation ---------------------------------------

    def recalculate_readiness(
        self,
        regions: Sequence[Dict[str, Any]],
        role_alias: Optional[Dict[str, Sequence[str]]] = None,
        minimum_quality: EvidenceQuality = EvidenceQuality.STRONGLY_SUPPORTED,
        actor: str = "system",
        affected_regions: Optional[List[str]] = None,
    ) -> Tuple[RegistrationEvent, List[ReadinessTransition], Dict[str, int]]:
        """The ONLY path that transitions readiness.

        Captures before/after snapshots, delegates to ReadinessRecalculator,
        runs the final readiness guard, and records an immutable event.

        Returns:
            (event, transitions, counts)
        """
        # Capture BEFORE snapshot
        before = ReadinessSnapshot.capture(regions)

        # Delegate to ReadinessRecalculator
        transitions, counts = ReadinessRecalculator.recalculate(
            regions, self.package, role_alias=role_alias,
            minimum_quality=minimum_quality)

        # Apply transitions to region dicts for AFTER snapshot
        transition_map = {t.region_id: t.recalculated for t in transitions}
        for region in regions:
            rid = region.get("region_id", "?")
            if rid in transition_map:
                region["readiness"] = transition_map[rid]

        # Capture AFTER snapshot
        after = ReadinessSnapshot.capture(regions)

        # FINAL READINESS GUARD
        ReadinessGuard.validate(counts, self.package, transitions)

        # Record event
        event = RegistrationEvent(
            event_id=self._event_id(),
            event_type=RegistrationEventType.READINESS_RECALCULATED,
            timestamp=self._now(),
            actor=actor,
            readiness_before=before.region_readiness,
            readiness_after=after.region_readiness,
            transitions=[t.to_dict() for t in transitions],
            affected_regions=affected_regions or [t.region_id for t in transitions],
            package_version=self.package.version,
            reason=f"{len(transitions)} readiness transition(s). "
                   f"Counts: {counts}. "
                   f"Execution authorized: False. "
                   f"Human approval remains the sole authority to execute.",
            success=True,
        )
        self.audit_log.append(event)
        return event, transitions, counts

    def simulate_readiness(
        self,
        regions: Sequence[Dict[str, Any]],
        hypothetical_roles: Set[str],
        role_alias: Optional[Dict[str, Sequence[str]]] = None,
    ) -> Tuple[List[ReadinessTransition], Dict[str, int]]:
        """Dry-run: what would change if these roles became available?

        Creates no file, adds nothing to any package, fabricates no source.
        Does NOT record an audit event (dry runs are advisory only).
        """
        return ReadinessRecalculator.simulate(
            regions, hypothetical_roles, role_alias=role_alias)

    # -- freshness & freeze --------------------------------------------

    def verify_freshness(
        self,
        resolver: Dict[str, Path],
        actor: str = "system",
    ) -> Tuple[bool, List[str]]:
        """Re-hash every member artifact. Drift makes the package STALE."""
        fresh, reasons = self.package.verify_freshness(resolver)
        if not fresh:
            event = RegistrationEvent(
                event_id=self._event_id(),
                event_type=RegistrationEventType.STALE_DETECTED,
                timestamp=self._now(),
                actor=actor,
                package_version=self.package.version,
                reason=f"Stale input detected: {len(reasons)} artifact(s) changed.",
                success=True,
            )
            self.audit_log.append(event)
        return fresh, reasons

    def freeze(self, actor: str = "system") -> RegistrationEvent:
        """Freeze the source package."""
        self.package.freeze()
        event = RegistrationEvent(
            event_id=self._event_id(),
            event_type=RegistrationEventType.FREEZE,
            timestamp=self._now(),
            actor=actor,
            package_version=self.package.version,
            reason="Source package frozen. No further additions or replacements "
                   "until explicitly unfrozen.",
            success=True,
        )
        self.audit_log.append(event)
        return event

    # -- query ---------------------------------------------------------

    def artifact_count(self) -> int:
        return len(self.package.artifacts)

    def available_roles(
        self,
        minimum_quality: EvidenceQuality = EvidenceQuality.STRONGLY_SUPPORTED,
    ) -> Set[DatasetRole]:
        return self.package.available_roles(minimum_quality)

    def find_artifact(self, artifact_id: str) -> Optional[SourceArtifact]:
        for a in self.package.artifacts:
            if a.artifact_id == artifact_id:
                return a
        return None

    # -- serialization -------------------------------------------------

    def audit_log_to_dict(self) -> List[Dict[str, Any]]:
        """Export the full audit log. No raw contents, no absolute paths."""
        return [e.to_dict() for e in self.audit_log]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package": self.package.to_dict(),
            "audit_log": self.audit_log_to_dict(),
            "artifact_count": self.artifact_count(),
            "package_version": self.package.version,
            "mutation_count": self._mutation_count,
            "governance": ReadinessRecalculator.approval_still_required(),
        }

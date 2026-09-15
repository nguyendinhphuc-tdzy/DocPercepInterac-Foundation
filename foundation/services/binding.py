"""Provisional, bounded semantic/native association, independent of any engine.

This policy supports one exact, nonempty TEXT value. A candidate's existence
is not proof of association: the native reader must independently resolve its
typed address, verify the fingerprint, and return byte-for-byte equal text.
Candidate discovery remains replaceable. No normalization, confidence ranking,
fuzzy repair, execution readiness or production fidelity is inferred here.
Multi-object semantic spans require a separately qualified association policy.
"""

from hashlib import sha256
from dataclasses import dataclass
import json
import re
from typing import Iterable, Protocol

from foundation.domain import (
    DocumentVersion, DocumentVersionRef, NativeBinding, NativeLocator,
    PerceptionSnapshot, Ref, SemanticObject,
)
from foundation.domain.enums import BindingStatus, BusinessValueKind
from foundation.adapters.preflight.evidence import EvidenceArtifact


@dataclass(frozen=True)
class BindingResult:
    """Private evidence bundle; callers own append-only persistence and audit.

    The observation artifact contains native/semantic input records and must
    never be copied wholesale into sanitized public qualification summaries.
    """

    binding: NativeBinding
    observation_artifact: EvidenceArtifact
    configuration_artifact: EvidenceArtifact


class ExactNativeObservation(Protocol):
    status: str
    structural_fingerprint: str | None
    text: str | None


class ExactNativeResolver(Protocol):
    """Read-only adapter seam; fixture and real native providers are substitutable."""

    def resolve(self, document: DocumentVersion, locator: NativeLocator) -> ExactNativeObservation: ...


def _ref(record):
    return Ref(object_type=record.object_type, object_id=record.id, revision=record.revision)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class SemanticNativeBindingService:
    """B1.4 implementation only. RESOLVED is association, never authorization.

    Supply the complete candidate set for the intended scope. Caller-supplied
    confidence is deliberately absent from this interface. The snapshot is
    required because SemanticObject has no independent DocumentVersion field.
    Records are returned without persistence or in-place reverse-link changes.
    """

    METHOD = "exact-native-text-association/1.0.0;PROVISIONAL"

    def __init__(self, native_resolver: ExactNativeResolver):
        self._resolver = native_resolver

    @property
    def configuration_artifact(self) -> EvidenceArtifact:
        return EvidenceArtifact.create(dict(
            evaluator_key="foundation.b1.exact-native-text-association",
            evaluator_version="1.0.0", method=self.METHOD,
            policy="Nonempty TEXT exact equality after independent address and fingerprint verification; every supplied candidate evaluated; unresolved native candidates block association; multiple matches ambiguous.",
            production_qualified=False,
            limitations=["Candidate scope completeness and semantic fidelity require review.", "No multi-object span or non-TEXT association.", "No mutation or executable readiness."],
        ))

    def bind(
        self,
        document: DocumentVersion,
        snapshot: PerceptionSnapshot,
        semantic_object: SemanticObject,
        candidates: Iterable[NativeLocator],
    ) -> NativeBinding:
        return self.bind_with_evidence(document, snapshot, semantic_object, candidates).binding

    def bind_with_evidence(
        self,
        document: DocumentVersion,
        snapshot: PerceptionSnapshot,
        semantic_object: SemanticObject,
        candidates: Iterable[NativeLocator],
    ) -> BindingResult:
        ordered = sorted(candidates, key=lambda x: (x.id, x.revision, x.model_dump_json()))
        version = DocumentVersionRef(document_id=document.document_id, version_id=document.id, binary_hash=document.binary_hash)
        semantic_ref = _ref(semantic_object)
        observations = []

        def result(status, reason, locators=()):
            # Hash all governing inputs, not only mutable caller-selected IDs.
            payload = dict(method=self.METHOD, configuration_ref=self.configuration_artifact.ref.model_dump(mode="json"), document=document.model_dump(mode="json"), snapshot=snapshot.model_dump(mode="json"), semantic=semantic_object.model_dump(mode="json"), candidates=[x.model_dump(mode="json") for x in ordered], observations=observations, status=status.value, reason=reason)
            identity = "binding-" + sha256(_canonical(payload).encode("utf-8")).hexdigest()
            binding = NativeBinding(
                schema_version="0.1.0", object_type="NativeBinding", id=identity,
                revision=1, task_id=document.task_id, created_at=snapshot.created_at,
                semantic_object_ref=semantic_ref,
                native_locator_refs=[_ref(x) for x in locators], status=status,
                method=self.METHOD, reason=reason,
            )
            return BindingResult(binding, EvidenceArtifact.create(payload), self.configuration_artifact)

        if snapshot.task_id != document.task_id or semantic_object.task_id != document.task_id or any(x.task_id != document.task_id for x in ordered):
            return result(BindingStatus.UNSUPPORTED, "TASK_MISMATCH: association refused.")
        if snapshot.document_version_ref != version or any(x.document_version_ref != version for x in ordered):
            return result(BindingStatus.UNSUPPORTED, "STALE_DOCUMENT_VERSION: association refused.")
        if semantic_object.semantic_reference.snapshot_ref != _ref(snapshot) or snapshot.semantic_object_refs.count(semantic_ref) != 1:
            return result(BindingStatus.UNSUPPORTED, "SNAPSHOT_MEMBERSHIP_MISMATCH: semantic version provenance is not established.")
        if semantic_object.value.kind != BusinessValueKind.TEXT or not semantic_object.value.value:
            return result(BindingStatus.UNSUPPORTED, "UNSUPPORTED_VALUE: only nonempty exact TEXT association is implemented.")
        if not ordered:
            return result(BindingStatus.UNSUPPORTED, "NATIVE_BINDING_MISSING: no candidates; no executable readiness.")

        by_ref = {}
        for locator in ordered:
            key = (locator.id, locator.revision)
            if key in by_ref and by_ref[key] != locator:
                return result(BindingStatus.UNSUPPORTED, "CONFLICTING_CANDIDATE_RECORD: immutable locator identity has different content.")
            by_ref[key] = locator
        unique = list(by_ref.values())
        matches, failures = [], []
        for locator in unique:
            try:
                observation = self._resolver.resolve(document, locator)
                status = observation.status
                fingerprint = observation.structural_fingerprint
                text = observation.text
                if not isinstance(status, str) or (fingerprint is not None and (not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None)) or (text is not None and not isinstance(text, str)):
                    raise ValueError("Malformed native observation")
                if status not in {"EXACT_MATCH", "NOT_FOUND", "AMBIGUOUS", "UNSUPPORTED", "FINGERPRINT_MISMATCH", "STALE_DOCUMENT_VERSION"}:
                    status = "UNSUPPORTED"
                if status == "EXACT_MATCH" and fingerprint != locator.structural_fingerprint:
                    status = "FINGERPRINT_MISMATCH"
                equal = status == "EXACT_MATCH" and text == semantic_object.value.value
            except Exception:
                # Provider failures cannot become a successful association or
                # leak native/private reader exception details into the record.
                status, fingerprint, equal = "NATIVE_RESOLUTION_FAILED", None, False
            observations.append(dict(locator=locator.id, revision=locator.revision, status=status, fingerprint=fingerprint, exact_text_equal=equal))
            if status != "EXACT_MATCH":
                failures.append(status)
            elif equal:
                matches.append(locator)
        if failures:
            status = BindingStatus.AMBIGUOUS if set(failures) == {"AMBIGUOUS"} else BindingStatus.UNSUPPORTED
            return result(status, "Native resolution refused: " + ", ".join(sorted(set(failures))) + "; no association selected.", unique)
        if len(matches) > 1:
            return result(BindingStatus.AMBIGUOUS, "Multiple exact text associations remain; no candidate was selected.", matches)
        if not matches:
            return result(BindingStatus.UNSUPPORTED, "NATIVE_BINDING_MISSING: no exact text association; no fuzzy fallback.", unique)
        return result(BindingStatus.RESOLVED, "One version-bound, fingerprint-verified exact text association within supplied candidates; not business fidelity, mutation capability or authorization.", matches)

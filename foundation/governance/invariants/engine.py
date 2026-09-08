"""Registry-backed enforcement of B0-observable frozen invariants."""

from __future__ import annotations

from collections.abc import Callable

from foundation.domain import (
    ActorType,
    ApprovedChangeSet,
    ApprovedChangeSetStatus,
    CapabilityStatus,
    CapabilitySupportedCondition,
    ChangeProposal,
    ChangeProposalStatus,
    CheckOutcome,
    DocumentArtifact,
    DocumentVersion,
    ErrorCode,
    EvidenceAssessment,
    EvidenceStatus,
    EventType,
    FreshnessOutcome,
    FreshnessPolicy,
    NativeBinding,
    NativeLocator,
    ObjectType,
    Ref,
    ReviewDecision,
    ReviewOutcome,
    RuleEvaluation,
    BusinessRule,
    SourceAssessment,
    SourceAssessmentStatus,
    SourceSufficiencyOutcome,
    TargetRegion,
    TargetVerificationStatus,
    TaskStatus,
    ReleaseStatus,
)
from foundation.governance.authorization import verify_authorization_digest

from .models import InvariantContext, InvariantResult


Checker = Callable[[InvariantContext], InvariantResult]


def _ref(record) -> Ref:
    return Ref(object_type=record.object_type, object_id=record.id, revision=record.revision)


class _Graph:
    def __init__(self, context: InvariantContext):
        self.records = {
            (item.object_type, item.id, item.revision): item
            for item in context.records
            if hasattr(item, "object_type")
        }

    def resolve(self, reference: Ref):
        return self.records.get((reference.object_type, reference.object_id, reference.revision))

    def of_type(self, object_type: ObjectType):
        return [item for (kind, _, _), item in self.records.items() if kind is object_type]

    def latest(self, object_type: ObjectType):
        by_id = {}
        for item in self.of_type(object_type):
            if item.id not in by_id or item.revision > by_id[item.id].revision:
                by_id[item.id] = item
        return list(by_id.values())


def _pass(invariant_id: str, reason: str) -> InvariantResult:
    return InvariantResult(invariant_id=invariant_id, passed=True, error_code=None, affected_refs=[], blocking=False, reason=reason)


def _fail(invariant_id: str, code: ErrorCode, reason: str, affected=()) -> InvariantResult:
    return InvariantResult(invariant_id=invariant_id, passed=False, error_code=code, affected_refs=[_ref(item) for item in affected], blocking=True, reason=reason)


def _doc(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for version in graph.of_type(ObjectType.DOCUMENT_VERSION):
        if not isinstance(version, DocumentVersion) or version.revision != 1 or version.binary_hash != version.content_ref.sha256:
            return _fail("FND-INV-DOC-001", ErrorCode.INVALID_CONTRACT, "DocumentVersion identity is not immutable", (version,))
    for artifact in graph.of_type(ObjectType.DOCUMENT_ARTIFACT):
        if not isinstance(artifact, DocumentArtifact):
            continue
        for version_ref in artifact.version_refs:
            version = graph.records.get((ObjectType.DOCUMENT_VERSION, version_ref.version_id, 1))
            if version is None or version.document_id != version_ref.document_id or version.binary_hash != version_ref.binary_hash:
                return _fail("FND-INV-DOC-001", ErrorCode.INVALID_CONTRACT, "DocumentVersionRef does not resolve to exact bytes", (artifact,))
    return _pass("FND-INV-DOC-001", "immutable document identities are consistent")


def _id_separation(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    locators = graph.of_type(ObjectType.NATIVE_LOCATOR)
    semantic = graph.of_type(ObjectType.SEMANTIC_OBJECT)
    targets = graph.of_type(ObjectType.TARGET_REGION)
    semantic_ids = {item.semantic_reference.semantic_id for item in semantic}
    locator_ids = {item.id for item in locators}
    business_ids = {item.business_target_id for item in targets}
    if semantic_ids & locator_ids or semantic_ids & business_ids or locator_ids & business_ids:
        return _fail("FND-INV-ID-001", ErrorCode.INVALID_CONTRACT, "business, semantic, and native identities overlap")
    return _pass("FND-INV-ID-001", "identity namespaces remain separate")


def _native_binding(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        for change in change_set.authorization.approved_changes:
            if not isinstance(graph.resolve(change.native_locator_ref), NativeLocator):
                return _fail("FND-INV-ID-002", ErrorCode.NATIVE_BINDING_MISSING, "approved change does not name a NativeLocator", (change_set,))
    for binding in graph.of_type(ObjectType.NATIVE_BINDING):
        if not isinstance(binding, NativeBinding) or graph.resolve(binding.semantic_object_ref) is None:
            return _fail("FND-INV-ID-002", ErrorCode.NATIVE_BINDING_MISSING, "NativeBinding association is unresolved", (binding,))
    return _pass("FND-INV-ID-002", "bindings associate semantics while changes name locators")


def _locator(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    observations = {item.locator_ref: item for item in context.locator_observations}
    needed = [change.native_locator_ref for item in graph.of_type(ObjectType.APPROVED_CHANGE_SET) for change in item.authorization.approved_changes]
    for locator_ref in needed:
        locator = graph.resolve(locator_ref)
        observation = observations.get(locator_ref)
        if not isinstance(locator, NativeLocator) or observation is None:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_NOT_FOUND, "exact locator observation is unavailable")
        if observation.match_count == 0:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_NOT_FOUND, "locator resolved no object", (locator,))
        if observation.match_count != 1:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_AMBIGUOUS, "locator did not resolve uniquely", (locator,))
        if observation.fuzzy_fallback_used or not observation.exact_address_used:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_AMBIGUOUS, "fuzzy execution is forbidden", (locator,))
        if observation.document_version_ref != locator.document_version_ref or observation.observed_structural_fingerprint != locator.structural_fingerprint:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_FINGERPRINT_MISMATCH, "locator version or fingerprint mismatch", (locator,))
    return _pass("FND-INV-LOC-001", "every executable locator has one exact matching observation")


def _capability(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        for change in change_set.authorization.approved_changes:
            conditions = [
                item
                for item in (*change_set.authorization.preconditions, *change.preconditions)
                if isinstance(item, CapabilitySupportedCondition)
                and item.native_locator_ref == change.native_locator_ref
                and item.operation is change.operation
            ]
            if not conditions:
                return _fail("FND-INV-CAP-001", ErrorCode.CAPABILITY_UNKNOWN, "approved change lacks capability condition", (change_set,))
            for condition in conditions:
                assessment = graph.resolve(condition.capability_result_ref.preflight_assessment_ref)
                if assessment is None:
                    return _fail("FND-INV-CAP-001", ErrorCode.CAPABILITY_UNKNOWN, "capability assessment is unavailable", (change_set,))
                result = next((item for item in assessment.capability_results if item.capability_result_id == condition.capability_result_ref.capability_result_id), None)
                if result is None or result.status is not CapabilityStatus.SUPPORTED or result.operation is not change.operation or change.native_locator_ref not in result.native_locator_refs:
                    return _fail("FND-INV-CAP-001", ErrorCode.EXECUTION_UNSUPPORTED, "operation-specific capability is not qualified", (change_set,))
    return _pass("FND-INV-CAP-001", "approved operations have exact qualified capability evidence")


def _evaluators(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for evaluation in graph.of_type(ObjectType.RULE_EVALUATION):
        rule = graph.resolve(evaluation.business_rule_ref)
        if not isinstance(rule, BusinessRule) or evaluation.evaluator_binding.evaluator_key != rule.evaluator_key:
            return _fail("FND-INV-EVAL-001", ErrorCode.EVALUATOR_CONFIGURATION_MISMATCH, "rule evaluator identity does not match", (evaluation,))
    for item in graph.of_type(ObjectType.SOURCE_ASSESSMENT) + graph.of_type(ObjectType.EVIDENCE_CHECK) + graph.of_type(ObjectType.EVIDENCE_ASSESSMENT):
        binding = item.evaluator_binding
        if not binding.evaluator_key or not binding.evaluator_version:
            return _fail("FND-INV-EVAL-001", ErrorCode.EVALUATOR_BINDING_UNAVAILABLE, "deterministic evaluator identity is incomplete", (item,))
    return _pass("FND-INV-EVAL-001", "deterministic evaluator identity and configuration are pinned")


def _sources(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        for reference in change_set.authorization.source_assessment_refs:
            item = graph.resolve(reference)
            if not isinstance(item, SourceAssessment) or item.status is not SourceAssessmentStatus.COMPLETED or item.outcome is not SourceSufficiencyOutcome.SUFFICIENT:
                return _fail("FND-INV-SRC-001", ErrorCode.SOURCE_MISSING, "authorization depends on insufficient source", (change_set,))
    return _pass("FND-INV-SRC-001", "blocking source gaps never enter authorization")


def _evidence(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        for reference in change_set.authorization.evidence_assessment_refs:
            item = graph.resolve(reference)
            if not isinstance(item, EvidenceAssessment) or item.status is not EvidenceStatus.VERIFIED:
                return _fail("FND-INV-EVD-001", ErrorCode.EVIDENCE_NOT_VERIFIED, "authorization depends on unverified evidence", (change_set,))
            checks = [graph.resolve(ref) for ref in item.evidence_check_refs]
            if any(check is None or check.outcome is not CheckOutcome.PASS for check in checks):
                return _fail("FND-INV-EVD-001", ErrorCode.EVIDENCE_INSUFFICIENT, "VERIFIED evidence has a non-passing deterministic check", (item,))
    return _pass("FND-INV-EVD-001", "verification is supported by deterministic passing checks")


def _freshness(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for assessment in graph.of_type(ObjectType.SOURCE_ASSESSMENT):
        if assessment.outcome is SourceSufficiencyOutcome.SUFFICIENT:
            evaluation = assessment.freshness_evaluation
            policy = graph.resolve(assessment.freshness_policy_ref)
            if evaluation is None or evaluation.outcome is not FreshnessOutcome.PASS or not isinstance(policy, FreshnessPolicy) or evaluation.freshness_policy_ref != assessment.freshness_policy_ref or evaluation.evaluator_key != policy.evaluator_key:
                return _fail("FND-INV-FRESH-001", ErrorCode.SOURCE_STALE, "sufficient source lacks an independent passing freshness evaluation", (assessment,))
    return _pass("FND-INV-FRESH-001", "period and freshness evidence are independently recorded")


def _ai(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for decision in graph.of_type(ObjectType.REVIEW_DECISION):
        if isinstance(decision, ReviewDecision) and decision.reviewer.actor_type is ActorType.AI:
            return _fail("FND-INV-AI-001", ErrorCode.AI_AUTHORITY_VIOLATION, "AI cannot issue ReviewDecision", (decision,))
    return _pass("FND-INV-AI-001", "AI records carry no verification or execution authority")


def _proposal_authority(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        for change in change_set.authorization.approved_changes:
            proposal = graph.resolve(change.change_proposal_ref)
            decision = graph.resolve(change.review_decision_ref)
            if not isinstance(proposal, ChangeProposal) or proposal.status is not ChangeProposalStatus.APPROVED:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_REQUIRED, "approved change lacks an approved proposal", (change_set,))
            if not isinstance(decision, ReviewDecision) or decision.outcome is not ReviewOutcome.APPROVE or decision.reviewer.actor_type is not ActorType.HUMAN:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_REQUIRED, "approved change lacks explicit human approval", (change_set,))
    return _pass("FND-INV-AUTH-001", "proposals alone never create execution authority")


def _sealed(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for item in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not verify_authorization_digest(item):
            return _fail("FND-INV-AUTH-002", ErrorCode.APPROVAL_CONTENT_MISMATCH, "authorization digest mismatch", (item,))
    return _pass("FND-INV-AUTH-002", "sealed authorization digests match RFC 8785 content")


def _authorization_state(context: InvariantContext) -> InvariantResult:
    for item in _Graph(context).of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(item.status, ApprovedChangeSetStatus):
            return _fail("FND-INV-AUTH-003", ErrorCode.INVALID_STATE_TRANSITION, "authorization contains a foreign lifecycle state", (item,))
    return _pass("FND-INV-AUTH-003", "authorization lifecycle remains independent")


def _replay(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    for request in context.replay_requests:
        change_set = graph.resolve(request.approved_change_set_ref)
        if not isinstance(change_set, ApprovedChangeSet):
            return _fail("FND-INV-REPLAY-001", ErrorCode.INVALID_CONTRACT, "ReplayRequest does not resolve to ApprovedChangeSet")
        if change_set.status is not ApprovedChangeSetStatus.APPROVED:
            return _fail("FND-INV-REPLAY-001", ErrorCode.AUTHORIZATION_NOT_APPROVED, "ReplayRequest references invalid authorization", (change_set,))
    return _pass("FND-INV-REPLAY-001", "replay requests contain only execution identity and approved authorization")


def _release(context: InvariantContext) -> InvariantResult:
    graph = _Graph(context)
    regions = {item.business_target_id: item for item in graph.latest(ObjectType.TARGET_REGION)}
    for task in graph.latest(ObjectType.FOUNDATION_TASK):
        incomplete = [target for target in task.required_business_target_ids if target not in regions or regions[target].verification_status is not TargetVerificationStatus.VERIFIED]
        if incomplete and (task.status is TaskStatus.COMPLETED or task.release_status is not ReleaseStatus.WITHHELD):
            return _fail("FND-INV-REL-001", ErrorCode.RELEASE_BLOCKED_INCOMPLETE_TARGETS, "incomplete required targets cannot imply release", (task,))
    return _pass("FND-INV-REL-001", "partial progress does not imply whole-task release")


INVARIANT_REGISTRY: dict[str, Checker] = {
    "FND-INV-DOC-001": _doc,
    "FND-INV-ID-001": _id_separation,
    "FND-INV-ID-002": _native_binding,
    "FND-INV-LOC-001": _locator,
    "FND-INV-CAP-001": _capability,
    "FND-INV-EVAL-001": _evaluators,
    "FND-INV-SRC-001": _sources,
    "FND-INV-EVD-001": _evidence,
    "FND-INV-FRESH-001": _freshness,
    "FND-INV-AI-001": _ai,
    "FND-INV-AUTH-001": _proposal_authority,
    "FND-INV-AUTH-002": _sealed,
    "FND-INV-AUTH-003": _authorization_state,
    "FND-INV-REPLAY-001": _replay,
    "FND-INV-REL-001": _release,
}
INVARIANT_IDS = frozenset(INVARIANT_REGISTRY)


class InvariantEngine:
    def evaluate(self, invariant_id: str, context: InvariantContext) -> InvariantResult:
        try:
            checker = INVARIANT_REGISTRY[invariant_id]
        except KeyError as error:
            raise ValueError(f"unknown frozen invariant ID {invariant_id}") from error
        return checker(context)

    def evaluate_all(self, context: InvariantContext) -> tuple[InvariantResult, ...]:
        return tuple(self.evaluate(identifier, context) for identifier in sorted(INVARIANT_REGISTRY))

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
    DocumentPreflightAssessment,
    DocumentPreflightStatus,
    DocumentVersion,
    ErrorCode,
    EvidenceAssessment,
    EvidenceStatus,
    FreshnessOutcome,
    FreshnessPolicy,
    NativeBinding,
    NativeLocator,
    ObjectType,
    Ref,
    ReleaseStatus,
    ReviewDecision,
    ReviewOutcome,
    RuleEvaluation,
    BusinessRule,
    SourceRequirement,
    SourceAssessment,
    SourceAssessmentStatus,
    SourceSufficiencyOutcome,
    TargetContractDefinition,
    TargetContractInstance,
    TargetRegion,
    TargetRegionDefinition,
    TargetVerificationStatus,
    TaskStatus,
    RulePack,
)
from foundation.governance.authorization import verify_authorization_digest

from .graph import GovernanceGraph
from .models import InvariantContext, InvariantResult


Checker = Callable[[InvariantContext], InvariantResult]


def _ref(record) -> Ref:
    return Ref(object_type=record.object_type, object_id=record.id, revision=record.revision)


def _pass(invariant_id: str, reason: str) -> InvariantResult:
    return InvariantResult(
        invariant_id=invariant_id,
        passed=True,
        error_code=None,
        affected_refs=[],
        blocking=False,
        reason=reason,
    )


def _fail(invariant_id: str, code: ErrorCode, reason: str, affected=()) -> InvariantResult:
    return InvariantResult(
        invariant_id=invariant_id,
        passed=False,
        error_code=code,
        affected_refs=[_ref(item) for item in affected if hasattr(item, "object_type")],
        blocking=True,
        reason=reason,
    )


def _doc(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for version in graph.of_type(ObjectType.DOCUMENT_VERSION):
        if (
            not isinstance(version, DocumentVersion)
            or version.revision != 1
            or version.binary_hash != version.content_ref.sha256
        ):
            return _fail(
                "FND-INV-DOC-001",
                ErrorCode.INVALID_CONTRACT,
                "DocumentVersion identity is not immutable",
                (version,),
            )
    for artifact in graph.of_type(ObjectType.DOCUMENT_ARTIFACT):
        if not isinstance(artifact, DocumentArtifact):
            continue
        for version_ref in artifact.version_refs:
            version = graph.resolve_document(version_ref, artifact.task_id)
            if version is None:
                return _fail(
                    "FND-INV-DOC-001",
                    ErrorCode.INVALID_CONTRACT,
                    "DocumentVersionRef does not resolve to exact task-owned bytes",
                    (artifact,),
                )
    return _pass("FND-INV-DOC-001", "immutable document identities are consistent")


def _id_separation(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    locators = graph.of_type(ObjectType.NATIVE_LOCATOR)
    semantic = graph.of_type(ObjectType.SEMANTIC_OBJECT)
    targets = graph.of_type(ObjectType.TARGET_REGION)
    semantic_ids = {item.semantic_reference.semantic_id for item in semantic}
    locator_ids = {item.id for item in locators}
    business_ids = {item.business_target_id for item in targets}
    if semantic_ids & locator_ids or semantic_ids & business_ids or locator_ids & business_ids:
        return _fail(
            "FND-INV-ID-001",
            ErrorCode.INVALID_CONTRACT,
            "business, semantic, and native identities overlap",
        )
    return _pass("FND-INV-ID-001", "identity namespaces remain separate")


def _native_binding(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(change_set, ApprovedChangeSet):
            continue
        for change in change_set.authorization.approved_changes:
            if not isinstance(graph.resolve(change.native_locator_ref, change_set.task_id), NativeLocator):
                return _fail(
                    "FND-INV-ID-002",
                    ErrorCode.NATIVE_BINDING_MISSING,
                    "approved change does not name a task-owned NativeLocator",
                    (change_set,),
                )
    for binding in graph.of_type(ObjectType.NATIVE_BINDING):
        if not isinstance(binding, NativeBinding):
            continue
        if graph.resolve(binding.semantic_object_ref, binding.task_id) is None:
            return _fail(
                "FND-INV-ID-002",
                ErrorCode.NATIVE_BINDING_MISSING,
                "NativeBinding semantic association is unresolved or cross-task",
                (binding,),
            )
        if any(graph.resolve(ref, binding.task_id) is None for ref in binding.native_locator_refs):
            return _fail(
                "FND-INV-ID-002",
                ErrorCode.NATIVE_BINDING_MISSING,
                "NativeBinding native association is unresolved or cross-task",
                (binding,),
            )
    return _pass("FND-INV-ID-002", "bindings associate semantics while changes name locators")


def _locator(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    needed = [
        (change_set.task_id, change.native_locator_ref)
        for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET)
        if isinstance(change_set, ApprovedChangeSet)
        for change in change_set.authorization.approved_changes
    ]
    for task_id, locator_ref in needed:
        locator = graph.resolve(locator_ref, task_id)
        observations = [
            item
            for item in context.locator_observations
            if item.locator_ref == locator_ref
            and item.document_version_ref == getattr(locator, "document_version_ref", None)
        ]
        if not isinstance(locator, NativeLocator) or len(observations) != 1:
            return _fail(
                "FND-INV-LOC-001",
                ErrorCode.LOCATOR_NOT_FOUND,
                "one exact task-scoped locator observation is required",
                (locator,) if locator is not None else (),
            )
        observation = observations[0]
        if observation.match_count == 0:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_NOT_FOUND, "locator resolved no object", (locator,))
        if observation.match_count != 1:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_AMBIGUOUS, "locator did not resolve uniquely", (locator,))
        if observation.fuzzy_fallback_used or not observation.exact_address_used:
            return _fail("FND-INV-LOC-001", ErrorCode.LOCATOR_AMBIGUOUS, "fuzzy execution is forbidden", (locator,))
        if observation.observed_structural_fingerprint != locator.structural_fingerprint:
            return _fail(
                "FND-INV-LOC-001",
                ErrorCode.LOCATOR_FINGERPRINT_MISMATCH,
                "locator structural fingerprint mismatch",
                (locator,),
            )
    return _pass("FND-INV-LOC-001", "every executable locator has one exact matching observation")


def _capability(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(change_set, ApprovedChangeSet):
            continue
        authorization_conditions = [
            item
            for item in change_set.authorization.preconditions
            if isinstance(item, CapabilitySupportedCondition)
        ]
        for change in change_set.authorization.approved_changes:
            matching = [
                item
                for item in authorization_conditions
                + [nested for nested in change.preconditions if isinstance(nested, CapabilitySupportedCondition)]
                if item.native_locator_ref == change.native_locator_ref
                and item.operation is change.operation
            ]
            if not matching:
                return _fail(
                    "FND-INV-CAP-001",
                    ErrorCode.CAPABILITY_UNKNOWN,
                    "approved change lacks an exact capability condition",
                    (change_set,),
                )
            locator = graph.resolve(change.native_locator_ref, change_set.task_id)
            for condition in matching:
                assessment = graph.resolve(
                    condition.capability_result_ref.preflight_assessment_ref,
                    change_set.task_id,
                )
                if not isinstance(assessment, DocumentPreflightAssessment):
                    return _fail(
                        "FND-INV-CAP-001",
                        ErrorCode.CAPABILITY_UNKNOWN,
                        "capability preflight assessment is unavailable or cross-task",
                        (change_set,),
                    )
                result = next(
                    (
                        item
                        for item in assessment.capability_results
                        if item.capability_result_id
                        == condition.capability_result_ref.capability_result_id
                    ),
                    None,
                )
                exact = (
                    result is not None
                    and result.status is CapabilityStatus.SUPPORTED
                    and assessment.status is DocumentPreflightStatus.COMPLETED
                    and assessment.document_version_ref
                    == change_set.authorization.target_document_version_ref
                    and result.document_version_ref == change_set.authorization.target_document_version_ref
                    and result.document_version_ref == assessment.document_version_ref
                    and result.operation is change.operation
                    and result.operation is condition.operation
                    and result.engine == condition.engine
                    and result.engine_version == condition.engine_version
                    and result.conformance is condition.conformance
                    and bool(result.qualification_evidence_refs)
                    and change.native_locator_ref in result.native_locator_refs
                    and isinstance(locator, NativeLocator)
                    and locator.document_version_ref
                    == change_set.authorization.target_document_version_ref
                    and result.native_structure is locator.locator_type
                )
                if not exact:
                    return _fail(
                        "FND-INV-CAP-001",
                        ErrorCode.EXECUTION_UNSUPPORTED,
                        "capability tuple does not exactly match the approved operation",
                        (change_set,),
                    )
    return _pass("FND-INV-CAP-001", "approved operations have exact qualified capability evidence")


def _evaluators(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for evaluation in graph.of_type(ObjectType.RULE_EVALUATION):
        rule = graph.resolve(evaluation.business_rule_ref)
        if not isinstance(rule, BusinessRule) or evaluation.evaluator_binding.evaluator_key != rule.evaluator_key:
            return _fail(
                "FND-INV-EVAL-001",
                ErrorCode.EVALUATOR_CONFIGURATION_MISMATCH,
                "rule evaluator identity does not match",
                (evaluation,),
            )
    for item in (
        graph.of_type(ObjectType.SOURCE_ASSESSMENT)
        + graph.of_type(ObjectType.EVIDENCE_CHECK)
        + graph.of_type(ObjectType.EVIDENCE_ASSESSMENT)
    ):
        binding = item.evaluator_binding
        if not binding.evaluator_key or not binding.evaluator_version or not binding.configuration_ref:
            return _fail(
                "FND-INV-EVAL-001",
                ErrorCode.EVALUATOR_BINDING_UNAVAILABLE,
                "deterministic evaluator identity is incomplete",
                (item,),
            )
    return _pass("FND-INV-EVAL-001", "deterministic evaluator identity and configuration are pinned")


def _source_requirement_refs(
    graph: GovernanceGraph,
    change_set: ApprovedChangeSet,
    business_target_id: str,
) -> tuple[tuple[Ref, SourceRequirement], ...] | None:
    definition = graph.resolve(change_set.authorization.target_contract_definition_ref)
    rule_pack = graph.resolve(change_set.authorization.rule_pack_ref)
    if not isinstance(definition, TargetContractDefinition) or not isinstance(rule_pack, RulePack):
        return None
    candidates: list[Ref] = list(definition.source_requirement_refs)
    for region_definition_ref in definition.target_region_definition_refs:
        region_definition = graph.resolve(region_definition_ref)
        if not isinstance(region_definition, TargetRegionDefinition):
            return None
        if region_definition.business_target_id == business_target_id:
            candidates.extend(region_definition.source_requirement_refs)
    for region in graph.of_type(ObjectType.TARGET_REGION):
        if (
            isinstance(region, TargetRegion)
            and region.task_id == change_set.task_id
            and region.business_target_id == business_target_id
            and region.target_contract_instance_ref == change_set.authorization.target_contract_instance_ref
        ):
            candidates.extend(region.source_requirement_refs)
    for rule_ref in rule_pack.business_rule_refs:
        rule = graph.resolve(rule_ref)
        if not isinstance(rule, BusinessRule):
            return None
        if business_target_id in rule.business_target_ids:
            candidates.extend(rule.source_requirement_refs)
    unique: dict[tuple[ObjectType, str, int], Ref] = {
        (item.object_type, item.object_id, item.revision): item for item in candidates
    }
    resolved: list[tuple[Ref, SourceRequirement]] = []
    for requirement_ref in unique.values():
        requirement = graph.resolve(requirement_ref)
        if not isinstance(requirement, SourceRequirement):
            return None
        resolved.append((requirement_ref, requirement))
    return tuple(resolved)


def _source_failure_for_outcome(outcome: SourceSufficiencyOutcome | None) -> ErrorCode:
    return {
        SourceSufficiencyOutcome.MISSING: ErrorCode.SOURCE_MISSING,
        SourceSufficiencyOutcome.STALE: ErrorCode.SOURCE_STALE,
        SourceSufficiencyOutcome.CONFLICTING: ErrorCode.SOURCE_CONFLICTING,
        SourceSufficiencyOutcome.NOT_AUTHORITATIVE: ErrorCode.SOURCE_NOT_AUTHORITATIVE,
        SourceSufficiencyOutcome.AMBIGUOUS: ErrorCode.SOURCE_AMBIGUOUS,
    }.get(outcome, ErrorCode.SOURCE_MISSING)


def _sources(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(change_set, ApprovedChangeSet):
            continue
        for change in change_set.authorization.approved_changes:
            requirement_refs = _source_requirement_refs(graph, change_set, change.business_target_id)
            if requirement_refs is None:
                return _fail(
                    "FND-INV-SRC-001",
                    ErrorCode.REFERENCE_NOT_FOUND,
                    "pinned target and rule context cannot derive source requirements",
                    (change_set,),
                )
            requirements = [
                (requirement_ref, requirement)
                for requirement_ref, requirement in requirement_refs
                if requirement.business_target_id == change.business_target_id
                and requirement.blocking
            ]
            for requirement_ref, _requirement in requirements:
                selected = []
                for reference in change_set.authorization.source_assessment_refs:
                    item = graph.resolve(reference, change_set.task_id)
                    if (
                        isinstance(item, SourceAssessment)
                        and item.source_requirement_ref == requirement_ref
                        and item.business_target_id == change.business_target_id
                    ):
                        selected.append(item)
                if not selected:
                    return _fail(
                        "FND-INV-SRC-001",
                        ErrorCode.SOURCE_MISSING,
                        "authorization omits an applicable blocking SourceAssessment",
                        (change_set,),
                    )
                assessment = selected[0]
                if assessment.status is not SourceAssessmentStatus.COMPLETED or assessment.outcome is not SourceSufficiencyOutcome.SUFFICIENT:
                    return _fail(
                        "FND-INV-SRC-001",
                        _source_failure_for_outcome(assessment.outcome),
                        "applicable source assessment is not completed and sufficient",
                        (assessment,),
                    )
                freshness = assessment.freshness_evaluation
                policy = graph.resolve(assessment.freshness_policy_ref)
                if (
                    freshness is None
                    or freshness.outcome is not FreshnessOutcome.PASS
                    or not isinstance(policy, FreshnessPolicy)
                    or freshness.freshness_policy_ref != assessment.freshness_policy_ref
                    or freshness.evaluator_key != policy.evaluator_key
                ):
                    return _fail(
                        "FND-INV-SRC-001",
                        ErrorCode.SOURCE_STALE,
                        "applicable source lacks passing deterministic freshness evidence",
                        (assessment,),
                    )
                for candidate in graph.of_type(ObjectType.SOURCE_ASSESSMENT):
                    if (
                        isinstance(candidate, SourceAssessment)
                        and candidate.task_id == change_set.task_id
                        and candidate.source_requirement_ref == requirement_ref
                        and candidate.business_target_id == change.business_target_id
                        and candidate is not assessment
                        and candidate.status is not SourceAssessmentStatus.SUPERSEDED
                        and candidate.outcome is not SourceSufficiencyOutcome.SUFFICIENT
                    ):
                        return _fail(
                            "FND-INV-SRC-001",
                            _source_failure_for_outcome(candidate.outcome),
                            "an unresolved replacement assessment makes selected source evidence inapplicable",
                            (candidate,),
                        )
    return _pass("FND-INV-SRC-001", "every applicable blocking requirement has complete sufficient evidence")


def _evidence(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(change_set, ApprovedChangeSet):
            continue
        for reference in change_set.authorization.evidence_assessment_refs:
            item = graph.resolve(reference, change_set.task_id)
            if not isinstance(item, EvidenceAssessment) or item.status is not EvidenceStatus.VERIFIED:
                return _fail(
                    "FND-INV-EVD-001",
                    ErrorCode.EVIDENCE_NOT_VERIFIED,
                    "authorization depends on unverified or cross-task evidence",
                    (change_set,),
                )
            checks = [graph.resolve(ref, change_set.task_id) for ref in item.evidence_check_refs]
            if any(check is None or check.outcome is not CheckOutcome.PASS for check in checks):
                return _fail(
                    "FND-INV-EVD-001",
                    ErrorCode.EVIDENCE_INSUFFICIENT,
                    "VERIFIED evidence has a non-passing deterministic check",
                    (item,),
                )
    return _pass("FND-INV-EVD-001", "verification is supported by deterministic passing checks")


def _freshness(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for assessment in graph.of_type(ObjectType.SOURCE_ASSESSMENT):
        if isinstance(assessment, SourceAssessment) and assessment.outcome is SourceSufficiencyOutcome.SUFFICIENT:
            evaluation = assessment.freshness_evaluation
            policy = graph.resolve(assessment.freshness_policy_ref)
            if (
                evaluation is None
                or evaluation.outcome is not FreshnessOutcome.PASS
                or not isinstance(policy, FreshnessPolicy)
                or evaluation.freshness_policy_ref != assessment.freshness_policy_ref
                or evaluation.evaluator_key != policy.evaluator_key
            ):
                return _fail(
                    "FND-INV-FRESH-001",
                    ErrorCode.SOURCE_STALE,
                    "sufficient source lacks an independent passing freshness evaluation",
                    (assessment,),
                )
    return _pass("FND-INV-FRESH-001", "period and freshness evidence are independently recorded")


def _ai(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for decision in graph.of_type(ObjectType.REVIEW_DECISION):
        if isinstance(decision, ReviewDecision) and decision.reviewer.actor_type is ActorType.AI:
            return _fail(
                "FND-INV-AI-001",
                ErrorCode.AI_AUTHORITY_VIOLATION,
                "AI cannot issue ReviewDecision",
                (decision,),
            )
    return _pass("FND-INV-AI-001", "AI records carry no verification or execution authority")


def _proposal_content(proposal: ChangeProposal) -> dict:
    """Return all proposal fields except immutable lifecycle envelope fields."""

    return proposal.model_dump(mode="json", exclude={"revision", "created_at", "status"})


def _proposal_authority(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for change_set in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(change_set, ApprovedChangeSet):
            continue
        authorization = change_set.authorization
        target_instance = graph.resolve(
            authorization.target_contract_instance_ref,
            change_set.task_id,
        )
        if not isinstance(target_instance, TargetContractInstance):
            return _fail(
                "FND-INV-AUTH-001",
                ErrorCode.REFERENCE_NOT_FOUND,
                "authorization target contract instance is unresolved or cross-task",
                (change_set,),
            )
        target_document = graph.resolve_document(
            authorization.target_document_version_ref,
            change_set.task_id,
        )
        if not isinstance(target_document, DocumentVersion):
            return _fail(
                "FND-INV-AUTH-001",
                ErrorCode.REFERENCE_NOT_FOUND,
                "authorization target DocumentVersion is unresolved or cross-task",
                (change_set,),
            )
        if (
            target_instance.definition_ref
            != authorization.target_contract_definition_ref
            or target_instance.target_document_version_ref
            != authorization.target_document_version_ref
        ):
            return _fail(
                "FND-INV-AUTH-001",
                ErrorCode.APPROVAL_CONTENT_MISMATCH,
                "authorization target instance does not bind the sealed definition and document version",
                (change_set, target_instance),
            )
        for change in authorization.approved_changes:
            decision = graph.resolve(change.review_decision_ref, change_set.task_id)
            if not isinstance(decision, ReviewDecision):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_REQUIRED, "approved change lacks its task-owned ReviewDecision", (change_set,))
            if decision.reviewer.actor_type is ActorType.AI:
                return _fail("FND-INV-AUTH-001", ErrorCode.AI_AUTHORITY_VIOLATION, "only a human may authorize an approved change", (decision,))
            if decision.reviewer.actor_type is not ActorType.HUMAN:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_REQUIRED, "only a human may authorize an approved change", (decision,))
            if decision.outcome is not ReviewOutcome.APPROVE:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_REQUIRED, "ReviewDecision outcome is not APPROVE", (decision,))
            if change.review_decision_ref not in authorization.review_decision_refs:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "approved change decision is not sealed in authorization", (change_set,))
            reviewed = graph.resolve(decision.change_proposal_ref, change_set.task_id)
            approved = graph.resolve(change.change_proposal_ref, change_set.task_id)
            if not isinstance(reviewed, ChangeProposal) or not isinstance(approved, ChangeProposal):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "reviewed and approved proposals are unresolved", (change_set,))
            if reviewed.id != approved.id or reviewed.task_id != approved.task_id or approved.task_id != change_set.task_id:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "reviewed and approved proposals are not the same task-owned logical proposal", (change_set,))
            if reviewed.status is not ChangeProposalStatus.IN_REVIEW:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "ReviewDecision does not reference an IN_REVIEW proposal", (reviewed,))
            if approved.status is not ChangeProposalStatus.APPROVED or approved.revision != reviewed.revision + 1:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "approved proposal is not the immediate approved lifecycle successor", (approved,))
            if _proposal_content(reviewed) != _proposal_content(approved):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "authorization-relevant proposal content changed after review", (approved,))
            if (
                change.business_target_id != approved.business_target_id
                or change.native_locator_ref != approved.native_locator_ref
                or change.operation is not approved.operation
                or change.payload != approved.payload
                or authorization.target_document_version_ref != approved.target_document_version_ref
                or authorization.target_contract_definition_ref != approved.target_contract_definition_ref
                or authorization.target_contract_instance_ref != approved.target_contract_instance_ref
                or authorization.rule_pack_ref != approved.rule_pack_ref
            ):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "ApprovedChange does not match its approved proposal", (change_set,))
            if any(reference not in authorization.source_assessment_refs for reference in approved.source_assessment_refs):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "approved source assessments are not sealed in authorization", (change_set,))
            if any(reference not in authorization.evidence_assessment_refs for reference in approved.evidence_assessment_refs):
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "approved evidence assessments are not sealed in authorization", (change_set,))
            if graph.resolve(approved.native_locator_ref, change_set.task_id) is None:
                return _fail("FND-INV-AUTH-001", ErrorCode.APPROVAL_CONTENT_MISMATCH, "approved proposal locator is cross-task or unresolved", (approved,))
    return _pass("FND-INV-AUTH-001", "human review binds an immutable proposal successor to each approved change")


def _sealed(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for item in graph.of_type(ObjectType.APPROVED_CHANGE_SET):
        if not verify_authorization_digest(item):
            return _fail("FND-INV-AUTH-002", ErrorCode.APPROVAL_CONTENT_MISMATCH, "authorization digest mismatch", (item,))
    return _pass("FND-INV-AUTH-002", "sealed authorization digests match RFC 8785 content")


def _authorization_state(context: InvariantContext) -> InvariantResult:
    for item in GovernanceGraph(context.records).of_type(ObjectType.APPROVED_CHANGE_SET):
        if not isinstance(item.status, ApprovedChangeSetStatus):
            return _fail("FND-INV-AUTH-003", ErrorCode.INVALID_STATE_TRANSITION, "authorization contains a foreign lifecycle state", (item,))
    return _pass("FND-INV-AUTH-003", "authorization lifecycle remains independent")


def _replay(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for request in context.replay_requests:
        change_set = graph.resolve(request.approved_change_set_ref)
        if not isinstance(change_set, ApprovedChangeSet):
            return _fail("FND-INV-REPLAY-001", ErrorCode.INVALID_CONTRACT, "ReplayRequest does not resolve to ApprovedChangeSet")
        if change_set.status is not ApprovedChangeSetStatus.APPROVED:
            return _fail("FND-INV-REPLAY-001", ErrorCode.AUTHORIZATION_NOT_APPROVED, "ReplayRequest references invalid authorization", (change_set,))
    return _pass("FND-INV-REPLAY-001", "replay requests contain only execution identity and approved authorization")


def _release(context: InvariantContext) -> InvariantResult:
    graph = GovernanceGraph(context.records)
    for task in graph.latest(ObjectType.FOUNDATION_TASK):
        if not hasattr(task, "required_business_target_ids"):
            continue
        regions = {
            item.business_target_id: item
            for item in graph.latest(ObjectType.TARGET_REGION, task.task_id if hasattr(task, "task_id") else task.id)
            if isinstance(item, TargetRegion)
        }
        incomplete = [
            target
            for target in task.required_business_target_ids
            if target not in regions or regions[target].verification_status is not TargetVerificationStatus.VERIFIED
        ]
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

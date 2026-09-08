"""Foundation Contract v0.1 typed backend domain projection.

These classes describe immutable contract data. They do not implement
workflow transitions, authorization decisions, replay, or validation engines.
"""

from .audit import (
    AIInteractionMetadata,
    AuditEvent,
    AuditMetadata,
    DeterministicEvaluationMetadata,
    ExceptionMetadata,
    GovernanceMetadata,
    NativeBindingMetadata,
    PerceptionMetadata,
    ReplayMetadata,
    ValidationMetadata,
)
from .authorization import ApprovedChange, ApprovedChangeSet, AuthorizationBinding
from .base import *
from .documents import (
    AnalysisRun,
    CapabilityResult,
    DocumentArtifact,
    DocumentPreflightAssessment,
    DocumentVersion,
    FoundationTask,
    PreflightFinding,
)
from .enums import *
from .evidence import EvidenceAssessment, EvidenceCheck, EvidenceRecord
from .exceptions import ExceptionRecord
from .execution import ChangeExecutionResult, ExecutionResult, ReplayRequest
from .perception import NativeBinding, NativeLocator, PerceptionSnapshot, SemanticObject
from .proposals import AIInteractionRecord, ChangeProposal, MappingProposal
from .refs import Actor, ContentRef, DocumentVersionRef, EvaluatorBinding, Period, Ref, Reference, SemanticReference
from .registry import DOMAIN_RECORD_MODELS, parse_audit_event, parse_record
from .review import ReviewDecision
from .rules import BusinessRule, RuleEvaluation, RulePack
from .sources import FreshnessEvaluation, FreshnessPolicy, SourceAssessment, SourceRequirement
from .targets import TargetContractDefinition, TargetContractInstance, TargetRegion, TargetRegionDefinition
from .validation import ValidationCheckResult, ValidationPlan, ValidationReport
from .values import *


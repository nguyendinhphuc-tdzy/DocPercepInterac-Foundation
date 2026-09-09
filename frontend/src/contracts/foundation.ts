/**
 * Curated type-only frontend facade for Foundation Contract v0.1.
 *
 * Source of truth: docs/contracts/foundation.openapi.yaml
 * Generated projection: frontend/src/contracts/generated/foundation.ts
 *
 * All types in this facade are strictly type aliases projected from the
 * generated contract. No backend schemas, fields, or enums are duplicated manually.
 */

import type { components } from "./generated/foundation";

// ── Core Record Type Aliases ───────────────────────────────────────────────────

export type FoundationTask = components["schemas"]["FoundationTask"];
export type DocumentArtifact = components["schemas"]["DocumentArtifact"];
export type DocumentVersion = components["schemas"]["DocumentVersion"];
export type DocumentVersionRef = components["schemas"]["DocumentVersionRef"];

export type DocumentPreflightAssessment = components["schemas"]["DocumentPreflightAssessment"];
export type CapabilityResult = components["schemas"]["CapabilityResult"];

export type SourceAssessment = components["schemas"]["SourceAssessment"];
export type EvidenceAssessment = components["schemas"]["EvidenceAssessment"];

export type TargetRegion = components["schemas"]["TargetRegion"];
export type BusinessTargetID = components["schemas"]["BusinessTargetID"];
export type SemanticReference = components["schemas"]["SemanticReference"];
export type NativeLocator = components["schemas"]["NativeLocator"];
export type NativeBinding = components["schemas"]["NativeBinding"];

export type MappingProposal = components["schemas"]["MappingProposal"];
export type ChangeProposal = components["schemas"]["ChangeProposal"];
export type ReviewDecision = components["schemas"]["ReviewDecision"];
export type ApprovedChangeSet = components["schemas"]["ApprovedChangeSet"];

export type ExecutionResult = components["schemas"]["ExecutionResult"];
export type ValidationReport = components["schemas"]["ValidationReport"];
export type ExceptionRecord = components["schemas"]["ExceptionRecord"];
export type AuditEvent = components["schemas"]["AuditEvent"];

// ── Supporting Reference & Value Types ─────────────────────────────────────────

export type Ref = components["schemas"]["Ref"];
export type Actor = components["schemas"]["Actor"];
export type Period = components["schemas"]["Period"];
export type EvidenceRecord = components["schemas"]["EvidenceRecord"];
export type BusinessValue = components["schemas"]["BusinessValue"];
export type NativeAddress = components["schemas"]["NativeAddress"];
export type ObjectType = components["schemas"]["ObjectType"];
export type ErrorCode = components["schemas"]["ErrorCode"];

// ── Derived Inline Status & Outcome Enums ──────────────────────────────────────

export type TaskStatus = FoundationTask["status"];
export type TaskReleaseStatus = FoundationTask["release_status"];
export type DocumentStatus = DocumentArtifact["status"];
export type DocumentPreflightStatus = DocumentPreflightAssessment["status"];
export type SourceAssessmentStatus = SourceAssessment["status"];
export type SourceSufficiencyOutcome = SourceAssessment["outcome"];
export type EvidenceStatus = EvidenceAssessment["status"];
export type TargetVerificationStatus = TargetRegion["verification_status"];
export type ChangeProposalStatus = ChangeProposal["status"];
export type ApprovedChangeSetStatus = ApprovedChangeSet["status"];
export type ExecutionStatus = ExecutionResult["status"];
export type ValidationStatus = ValidationReport["status"];
export type ExceptionStatus = ExceptionRecord["status"];

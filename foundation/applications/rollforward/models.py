"""
Local File Roll-Forward Domain Models (V1 Contract)
===================================================
Location: foundation/applications/rollforward/models.py

Defines typed Pydantic v2 schemas for the Local File Roll-Forward workflow.
Guarantees immutable provenance, explicit lifecycle tracking, versioned manifests,
and strict approval gating prior to structural writeback.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field


class ManifestStatus(str, Enum):
    """Lifecycle states of the Roll-Forward Manifest."""
    DISCOVERED = "DISCOVERED"
    PLANNED = "PLANNED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    VALIDATED = "VALIDATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class RegionClassification(str, Enum):
    """Semantic roll-forward classification of a target document region."""
    STATIC = "STATIC"                      # Content is carried forward unchanged
    UPDATE = "UPDATE"                      # In-place scalar update (same row/table topology)
    REPEATABLE = "REPEATABLE"              # Table row expansion/cloning driven by current data
    REGENERATE = "REGENERATE"              # Reconstructed asset/diagram (e.g. ownership chart)
    ADD = "ADD"                            # Newly introduced section/table under new regulation
    REMOVE = "REMOVE"                      # Deprecated section/table eliminated in target
    MANUAL_REVIEW = "MANUAL_REVIEW"        # Ambiguous or high-risk region requiring tax reviewer input
    UNKNOWN = "UNKNOWN"                    # Unrecognized region; strictly blocked from auto-execution


class SourceBindingStatus(str, Enum):
    """Integrity and freshness status of a source data reference."""
    VERIFIED = "VERIFIED"                  # Deterministically verified against loaded document elements
    UNVERIFIED = "UNVERIFIED"              # Proposed binding not yet confirmed against document structure
    AMBIGUOUS = "AMBIGUOUS"                # Multiple candidate cells/elements match the query
    STALE = "STALE"                        # Source reference altered, shifted, or invalid post-edit
    MISSING = "MISSING"                    # Required source element/sheet not found in workspace


class SourceType(str, Enum):
    """Type of data source backing a roll-forward binding."""
    DOCX = "docx"
    XLSX = "xlsx"
    PDF = "pdf"
    SYSTEM = "system"


class ExecutionGate(str, Enum):
    """Region-level gate controlling eligibility for future structural mutation."""
    BLOCKED = "BLOCKED"                    # Blocked due to manual review, unverified source, or validation blocker
    READY = "READY"                        # Verified, non-stale, and approved for structural execution


class ValidationRuleType(str, Enum):
    """Explicit semantic validation rule types."""
    REQUIRED_REGION_PRESENT = "REQUIRED_REGION_PRESENT"
    ROW_COUNT_MATCH = "ROW_COUNT_MATCH"
    COLUMN_COUNT_UNCHANGED = "COLUMN_COUNT_UNCHANGED"
    MERGE_TOPOLOGY_PRESERVED = "MERGE_TOPOLOGY_PRESERVED"
    STYLE_PRESERVED = "STYLE_PRESERVED"
    SOURCE_VALUE_PRESENT = "SOURCE_VALUE_PRESENT"
    OUTPUT_VALUE_MATCH = "OUTPUT_VALUE_MATCH"
    IMAGE_PRESENT = "IMAGE_PRESENT"
    NO_ORPHAN_RELATIONSHIPS = "NO_ORPHAN_RELATIONSHIPS"
    ARITHMETIC_CONSTRAINT = "ARITHMETIC_CONSTRAINT"


class ValidationSeverity(str, Enum):
    """Severity of a validation rule failure."""
    BLOCKER = "BLOCKER"                    # Halts execution; cannot proceed to execution
    WARNING = "WARNING"                    # Flags discrepancy; requires reviewer notice


class DiffChangeType(str, Enum):
    """Classification of changes in the visual diff."""
    CONTENT_UPDATED = "CONTENT_UPDATED"
    ROW_ADDED = "ROW_ADDED"
    ROW_REMOVED = "ROW_REMOVED"
    STRUCTURE_CHANGED = "STRUCTURE_CHANGED"
    FIGURE_REPLACED = "FIGURE_REPLACED"
    STATIC_PRESERVED = "STATIC_PRESERVED"


class GroundTruthStatus(str, Enum):
    """Oracle comparison status (strictly for evaluation/testing against Ground Truth)."""
    VERIFIED = "VERIFIED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# SUB-COMPONENTS & VALUE OBJECTS
# ============================================================================

class HistoricalReference(BaseModel):
    """Authoritative reference to the previous-year Local File element."""
    doc_id: str
    doc_name: Optional[str] = None
    element_id: Optional[str] = None
    table_index: Optional[int] = None
    paragraph_index: Optional[int] = None
    value_snippet: Optional[str] = None
    ground_truth_status: GroundTruthStatus = GroundTruthStatus.VERIFIED


class SourceBinding(BaseModel):
    """Dual-format source reference binding to DOCX or XLSX data primitives."""
    source_doc_id: str
    source_doc_name: str
    source_type: SourceType = SourceType.XLSX
    sheet_name: Optional[str] = None
    cell_address: Optional[str] = None
    cell_range: Optional[str] = None
    element_id: Optional[str] = None       # Canonical Foundation element_id (if DOCX/PDF)
    match_basis: List[str] = Field(default_factory=list)
    status: SourceBindingStatus = SourceBindingStatus.VERIFIED
    reason: str = ""
    provenance: Dict[str, Any] = Field(default_factory=dict)

    def is_executable(self) -> bool:
        """Only VERIFIED (non-stale) bindings are safe for execution."""
        return self.status == SourceBindingStatus.VERIFIED


class StructuralDelta(BaseModel):
    """Explicit structural delta specification between template and target."""
    template_rows: int = Field(ge=0)
    target_rows: int = Field(ge=0)
    insert_count: int = Field(ge=0)
    delete_count: int = Field(ge=0)
    column_delta: int = 0
    merge_topology_changed: bool = False
    row_template_anchor: Optional[str] = None
    observation_source: str = "audit_comparison"
    observation_context: Dict[str, Any] = Field(default_factory=dict)


class RowTemplate(BaseModel):
    """Prototype row specification safe for structural cloning.

    NOTE: safe_to_clone describes structural XML topology validity only;
    it does NOT authorize execution without explicit manifest approval.
    """
    template_row_idx: int = Field(ge=0)
    row_anchor: str
    column_schemas: List[Dict[str, Any]] = Field(default_factory=list)
    cell_properties_policy: str = "INHERIT_PROTOTYPE"
    merge_policy: str = "RESET_VMERGE_RETAIN_GRIDSPAN"
    safe_to_clone: bool = True


class ValidationRule(BaseModel):
    """Typed constraint validated before and after document generation."""
    rule_type: ValidationRuleType
    severity: ValidationSeverity = ValidationSeverity.BLOCKER
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class FigureBinding(BaseModel):
    """Binding specification for embedded diagrams, charts, and images."""
    figure_id: str = Field(default_factory=lambda: f"fig-{uuid.uuid4().hex[:8]}")
    target_element_id: str
    target_doc_id: str
    historical_reference: Optional[HistoricalReference] = None
    current_source: Optional[SourceBinding] = None
    media_id: Optional[str] = None
    source_ref: Optional[str] = None
    strategy: RegionClassification = RegionClassification.STATIC
    validation_rules: List[ValidationRule] = Field(default_factory=list)


class RollForwardDiff(BaseModel):
    """Formal delta model for visual before/after comparison."""
    region_id: str
    change_type: DiffChangeType
    before_summary: Dict[str, Any] = Field(default_factory=dict)
    after_summary: Dict[str, Any] = Field(default_factory=dict)
    delta_details: List[Dict[str, Any]] = Field(default_factory=list)


class TransitionLog(BaseModel):
    """Immutable record of a lifecycle state transition."""
    log_id: str = Field(default_factory=lambda: f"log-{uuid.uuid4().hex[:8]}")
    from_state: ManifestStatus
    to_state: ManifestStatus
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: Literal["user", "agent", "system"]
    reason: str = ""
    manifest_version: int = 1


# ============================================================================
# PRIMARY ROLL-FORWARD REGION & MANIFEST
# ============================================================================

class RollForwardRegion(BaseModel):
    """An independently analyzed, governed target document region."""
    region_id: str = Field(default_factory=lambda: f"rfr-{uuid.uuid4().hex[:8]}")
    section_name: str
    target_document_id: str
    target_element_ids: List[str] = Field(default_factory=list)
    classification: RegionClassification = RegionClassification.UPDATE
    historical_reference: Optional[HistoricalReference] = None
    current_sources: List[SourceBinding] = Field(default_factory=list)
    structural_delta: Optional[StructuralDelta] = None
    row_template: Optional[RowTemplate] = None
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    mutation_strategy: str = "IN_PLACE_REPLACE"
    review_state: Literal["PENDING", "APPROVED", "REJECTED", "MANUAL_REQUIRED"] = "PENDING"
    notes: Optional[str] = None

    @property
    def execution_gate(self) -> ExecutionGate:
        """Evaluates whether this region is execution-ready or blocked.

        Gating rules:
        - UNKNOWN or MANUAL_REVIEW classifications are strictly BLOCKED.
        - Non-verified, ambiguous, or stale source bindings are strictly BLOCKED.
        - Explicit REJECTED review state is strictly BLOCKED.
        """
        if self.classification in (RegionClassification.UNKNOWN, RegionClassification.MANUAL_REVIEW):
            return ExecutionGate.BLOCKED
        if self.review_state == "REJECTED":
            return ExecutionGate.BLOCKED
        for src in self.current_sources:
            if not src.is_executable():
                return ExecutionGate.BLOCKED
        return ExecutionGate.READY

    def requires_manual_review(self) -> bool:
        """Returns True if this region cannot proceed without human reviewer action."""
        if self.classification in (RegionClassification.MANUAL_REVIEW, RegionClassification.UNKNOWN):
            return True
        for src in self.current_sources:
            if src.status in (SourceBindingStatus.AMBIGUOUS, SourceBindingStatus.MISSING, SourceBindingStatus.STALE):
                return True
        return False


class RollForwardManifest(BaseModel):
    """Top-level execution contract for Local File Roll-Forward."""
    schema_version: str = "1.0.0"
    manifest_version: int = 1
    parent_version: Optional[int] = None
    manifest_id: str = Field(default_factory=lambda: f"rfm-{uuid.uuid4().hex[:12]}")
    session_id: str
    historical_document_id: Optional[str] = None
    template_document_id: str
    current_source_document_ids: List[str] = Field(default_factory=list)
    status: ManifestStatus = ManifestStatus.DISCOVERED
    regions: List[RollForwardRegion] = Field(default_factory=list)
    figures: List[FigureBinding] = Field(default_factory=list)
    history: List[TransitionLog] = Field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    approved_manifest_version: Optional[int] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def has_unresolved_reviews(self) -> bool:
        """Determines if any region in the manifest requires manual review."""
        for r in self.regions:
            if r.requires_manual_review():
                return True
        for fig in self.figures:
            if fig.strategy == RegionClassification.MANUAL_REVIEW:
                return True
        return False

    def is_execution_ready(self) -> bool:
        """Validates that manifest is fully approved and all regions are unblocked."""
        if self.status != ManifestStatus.APPROVED:
            return False
        if self.approved_manifest_version != self.manifest_version:
            return False
        if not self.approved_by or not self.approved_at:
            return False
        for r in self.regions:
            if r.execution_gate != ExecutionGate.READY:
                return False
        return True

    def mark_modified(self, actor: Literal["user", "agent", "system"] = "agent") -> None:
        """Increments manifest version and invalidates existing approval if previously approved."""
        self.parent_version = self.manifest_version
        self.manifest_version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

        if self.status == ManifestStatus.APPROVED:
            # Invalidate approval on post-approval modification
            prev_status = self.status
            self.approved_by = None
            self.approved_at = None
            self.approved_manifest_version = None
            new_status = (
                ManifestStatus.REVIEW_REQUIRED
                if self.has_unresolved_reviews()
                else ManifestStatus.PLANNED
            )
            self.status = new_status
            self.history.append(
                TransitionLog(
                    from_state=prev_status,
                    to_state=new_status,
                    actor=actor,
                    reason=f"Manifest modified to version {self.manifest_version}; approval invalidated.",
                    manifest_version=self.manifest_version,
                )
            )

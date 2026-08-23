"""
Local File Roll-Forward Workflow Intake (Phase PROD-UX-1)
=========================================================
Location: foundation/applications/rollforward/workflow_intake.py

A structured intake contract for ONE named workflow, LOCAL_FILE_ROLL_FORWARD,
so a first-time user is guided into the correct workflow instead of landing in
a generic blank document workspace and guessing what files are required.

What this module owns
---------------------
    * The hardcoded workflow ROLES (three input slots). Filenames are never
      hardcoded and are never trusted as evidence of anything.
    * The typed InputSlot contract (cardinality, accepted formats, validation
      and readiness status per slot).
    * Deterministic slot/role validation, delegated wholly to the existing
      Phase E/F/G primitives: CorpusBuilder -> EvidencePolicyEngine ->
      SourceIntakeProfiler -> SourceRegistry -> ReadinessRecalculator.
    * A user-facing readiness summary over source DOMAINS (not role enums).
    * The required-input gate that keeps roll-forward execution blocked.
    * The structured workflow context handed to the Agent, so the Agent never
      has to infer the workflow from filenames.

What this module explicitly does NOT do
---------------------------------------
    ✗ No mutation of any document (this is intake + UX only).
    ✗ No writeback, no reconciliation, no perception-semantics change.
    ✗ No approval: the best readiness any domain reaches here is "eligible for
      human review", exactly as ReadinessRecalculator already guarantees.
    ✗ No silent acceptance of a file whose content does not match its slot.

Role detection is content-derived
---------------------------------
Every signal used to accept or reject a file comes from the artifact's own
EvidenceCorpus (paragraph/table/cell text), never from its filename:

    fiscal period   `FY<year>`, `year ended ... <year>` occurrences in the text
    template shape  unfilled placeholder markers (`FY20XX`, `XX`, `[insert]`)
    document shape  which dataset roles the canonical policy engine observes
    data shape      whether the policy engine says the artifact SATISFIES a
                    current-year role (not merely mentions it)

A prior-year Local File and a current-year final Local File are structurally
identical documents; the only honest discriminator is the fiscal period their
content states. That is why the historical slot cross-checks its period against
the current-year sources rather than pattern-matching a filename.
"""
from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple

from applications.rollforward.evidence_policy import (
    CorpusBuilder,
    DatasetRole,
    EvidenceCorpus,
    SupplyScope,
)
from applications.rollforward.source_intake import (
    ArtifactFormat,
    EXTENSION_FORMAT,
    ReadinessRecalculator,
    RecalculatedReadiness,
    SourceArtifact,
    SourceIntakeProfiler,
)
from applications.rollforward.source_registry import SourceRegistry

if TYPE_CHECKING:  # imported for typing only — the runtime import is local to
    # to_records()/from_records(), keeping this domain module free of any
    # dependency on how the state happens to be stored.
    from adapters.repository import WorkflowRecord, WorkflowSlotAssignmentRecord


# ============================================================================
# 1. WORKFLOW + SLOT VOCABULARY
# ============================================================================

class WorkflowType(str, Enum):
    """Workflows that have a dedicated structured intake."""
    LOCAL_FILE_ROLL_FORWARD = "LOCAL_FILE_ROLL_FORWARD"


class SlotId(str, Enum):
    """The three hardcoded input ROLES of LOCAL_FILE_ROLL_FORWARD."""
    HISTORICAL_LOCAL_FILE = "HISTORICAL_LOCAL_FILE"
    CURRENT_YEAR_SOURCES = "CURRENT_YEAR_SOURCES"
    MASTER_TEMPLATE = "MASTER_TEMPLATE"


class Cardinality(str, Enum):
    EXACTLY_ONE = "EXACTLY_ONE"
    ONE_OR_MORE = "ONE_OR_MORE"


class SlotValidationStatus(str, Enum):
    """Whether an assigned file's CONTENT matches the slot it was put in."""
    PENDING = "PENDING"                  # not profiled yet
    ROLE_CONFIRMED = "ROLE_CONFIRMED"    # content matches the requested role
    HUMAN_REVIEW = "HUMAN_REVIEW"        # cannot be confirmed deterministically
    ROLE_MISMATCH = "ROLE_MISMATCH"      # content contradicts the requested role
    FORMAT_REJECTED = "FORMAT_REJECTED"  # wrong file format for this slot


class SlotReadinessStatus(str, Enum):
    """Whether the slot's requirement is met."""
    EMPTY = "EMPTY"                # nothing assigned yet
    BLOCKED = "BLOCKED"            # assigned, but unusable and unacknowledged
    NEEDS_REVIEW = "NEEDS_REVIEW"  # assigned, flagged, human decision recorded
    SATISFIED = "SATISFIED"        # assigned and confirmed


class DomainStatus(str, Enum):
    """User-facing readiness of one source domain."""
    SUPPORTED = "SUPPORTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    MISSING_SOURCE = "MISSING_SOURCE"
    BLOCKED = "BLOCKED"


DOMAIN_STATUS_LABEL: Dict[DomainStatus, str] = {
    DomainStatus.SUPPORTED: "Ready",
    DomainStatus.HUMAN_REVIEW: "Human review",
    DomainStatus.MISSING_SOURCE: "Missing source",
    DomainStatus.BLOCKED: "Blocked",
}


class WorkflowIntakeError(RuntimeError):
    """Raised when an intake operation is not permitted."""


# ============================================================================
# 2. SLOT SPECIFICATION — roles are hardcoded, filenames never are
# ============================================================================

@dataclass(frozen=True)
class InputSlotSpec:
    slot_id: SlotId
    display_name: str
    section_title: str
    description: str
    required: bool
    cardinality: Cardinality
    accepted_formats: Tuple[ArtifactFormat, ...]
    supply_scope: SupplyScope
    expected_label: str
    add_action_label: str

    @property
    def accepts_multiple(self) -> bool:
        return self.cardinality == Cardinality.ONE_OR_MORE


SLOT_SPECS: Dict[SlotId, InputSlotSpec] = {
    SlotId.HISTORICAL_LOCAL_FILE: InputSlotSpec(
        slot_id=SlotId.HISTORICAL_LOCAL_FILE,
        display_name="Previous Local File",
        section_title="PREVIOUS LOCAL FILE",
        description="Last year's finalised Local File — the document being rolled forward.",
        required=True,
        cardinality=Cardinality.EXACTLY_ONE,
        accepted_formats=(ArtifactFormat.DOCX,),
        supply_scope=SupplyScope.HISTORICAL,
        expected_label="Historical Local File",
        add_action_label="Add Previous Local File",
    ),
    SlotId.CURRENT_YEAR_SOURCES: InputSlotSpec(
        slot_id=SlotId.CURRENT_YEAR_SOURCES,
        display_name="Current-Year Sources",
        section_title="CURRENT-YEAR SOURCES",
        description=(
            "Current-year financial, tax and supporting data that the roll-forward reads "
            "from. Add as many as the engagement has."
        ),
        required=True,
        cardinality=Cardinality.ONE_OR_MORE,
        accepted_formats=(ArtifactFormat.XLSX, ArtifactFormat.DOCX, ArtifactFormat.CSV),
        supply_scope=SupplyScope.ADDITIONAL,
        expected_label="Current-year source data",
        add_action_label="Add Source",
    ),
    SlotId.MASTER_TEMPLATE: InputSlotSpec(
        slot_id=SlotId.MASTER_TEMPLATE,
        display_name="Master Template",
        section_title="MASTER TEMPLATE",
        description="The blank master Local File template that defines this year's structure.",
        required=True,
        cardinality=Cardinality.EXACTLY_ONE,
        accepted_formats=(ArtifactFormat.DOCX,),
        supply_scope=SupplyScope.TEMPLATE,
        expected_label="Master Template",
        add_action_label="Add Master Template",
    ),
}

SLOT_ORDER: Tuple[SlotId, ...] = (
    SlotId.HISTORICAL_LOCAL_FILE,
    SlotId.CURRENT_YEAR_SOURCES,
    SlotId.MASTER_TEMPLATE,
)


# ============================================================================
# 3. SOURCE DOMAINS — what the readiness summary talks about
# ============================================================================

@dataclass(frozen=True)
class SourceDomain:
    """One user-facing row of the readiness summary.

    `roles` is an any-of set: the domain is supported when the current-year
    evidence satisfies at least one of them. Role enum names never reach the UI.
    """
    domain_id: str
    display_name: str
    roles: Tuple[DatasetRole, ...]
    missing_hint: str


SOURCE_DOMAINS: Tuple[SourceDomain, ...] = (
    SourceDomain(
        "RELATED_PARTY_TRANSACTIONS", "Related-party transactions",
        (DatasetRole.RELATED_PARTY_TRANSACTIONS,),
        "Add a current-year related-party transaction schedule.",
    ),
    SourceDomain(
        "FINANCIAL_INFORMATION", "Financial information",
        (DatasetRole.FINANCIAL_STATEMENTS, DatasetRole.FINANCIAL_ANALYSIS,
         DatasetRole.TAX_SCHEDULE, DatasetRole.FIXED_ASSETS,
         DatasetRole.INTEREST_EXPENSE, DatasetRole.SEGMENTED_DATA),
        "Add the current-year financial statements or tax schedule.",
    ),
    SourceDomain(
        "BENCHMARKING", "Benchmarking",
        (DatasetRole.BENCHMARKING_DATA, DatasetRole.COMPARABLE_COMPANIES,
         DatasetRole.IQR_RESULTS, DatasetRole.SCREENING_RESULTS),
        "Add this year's benchmarking study output.",
    ),
    SourceDomain(
        "FAR", "FAR",
        (DatasetRole.FAR,),
        "Add this year's functional analysis input.",
    ),
    SourceDomain(
        "ORGANISATION", "Organisation",
        (DatasetRole.ORGANIZATIONAL_DATA, DatasetRole.OWNERSHIP_STRUCTURE),
        "Add the current-year organisation chart or ownership structure.",
    ),
)


def _domain_regions() -> List[Dict[str, Any]]:
    """Requirement entries in the shape ReadinessRecalculator already consumes."""
    return [
        {
            "region_id": d.domain_id,
            "required_source_roles": [d.roles[0].value],
            "readiness": RecalculatedReadiness.BLOCKED_MISSING_SOURCE.value,
        }
        for d in SOURCE_DOMAINS
    ]


def _domain_role_alias() -> Dict[str, Sequence[str]]:
    """any-of alias map: primary role name -> every role that satisfies the domain."""
    return {d.roles[0].value: tuple(r.value for r in d.roles) for d in SOURCE_DOMAINS}


# ============================================================================
# 4. CONTENT SIGNALS — everything below is derived from the file's own text
# ============================================================================

# Matches a period anchor followed by the year it refers to, e.g. "FY<year>",
# "fiscal year <year>", "for the year ended 31 December <year>". The tempered
# repetition stops at the FIRST year after the anchor, so an intervening day
# and month ("31 December") cannot break the match or shift it onto a later
# number. No year is enumerated: any 19xx/20xx is equally acceptable.
_PERIOD_PATTERN = re.compile(
    r"(?:FY|fiscal\s+year|financial\s+year|year\s+ended|year\s+end|period\s+ended)"
    r"(?:(?!(?:19|20)\d{2}).){0,25}?((?:19|20)\d{2})",
    re.IGNORECASE | re.DOTALL,
)

# Unfilled template markers. A finalised Local File has none of these; a blank
# master template is full of them.
_PLACEHOLDER_PATTERN = re.compile(
    r"(FY\s?20XX|20XX|XXXX|\bXX\b|\[\s*insert[^\]]{0,30}\]|\[•\]|\bdd/mm\b)",
    re.IGNORECASE,
)

# Roles that only a Local File-shaped narrative document ever exhibits. A data
# workbook never carries a functional analysis or a business narrative.
_LOCAL_FILE_SHAPE_ROLES = frozenset({DatasetRole.FAR, DatasetRole.BUSINESS_NARRATIVE})

MIN_PERIOD_HITS = 3        # below this the period claim is not strong enough
MIN_PLACEHOLDER_HITS = 10  # below this the document is not a blank template


# ============================================================================
# 4a. FISCAL PERIODS — the roll-forward relationship, stated explicitly
# ============================================================================
#
# No year is ever special-cased. A period is whatever a document's own content
# states, and the workflow is defined by the RELATIONSHIP between two of them:
#
#     historical_period + expected_gap == current_period
#
# The invariant that actually gates the workflow is the weaker, timeless one:
# the historical period must strictly precede the current period. The expected
# gap is a separate, explicit expectation: a roll-forward normally moves one
# period forward, so a wider jump is surfaced for a human rather than accepted
# silently or rejected outright.

EXPECTED_ROLL_FORWARD_GAP_YEARS = 1


class PeriodRelationship(str, Enum):
    """How the historical period relates to the current one."""
    UNKNOWN = "UNKNOWN"          # at least one side states no period
    CONSECUTIVE = "CONSECUTIVE"  # exactly the expected gap apart
    WIDE_GAP = "WIDE_GAP"        # historical precedes current, but by more than expected
    SAME_PERIOD = "SAME_PERIOD"  # both sides cover the same period
    INVERTED = "INVERTED"        # historical is later than current


@dataclass(frozen=True, order=True)
class FiscalPeriod:
    """One fiscal period, identified by the year the content states."""
    year: int

    @property
    def label(self) -> str:
        return f"FY{self.year}"

    def precedes(self, other: "FiscalPeriod") -> bool:
        return self.year < other.year

    def gap_to(self, other: "FiscalPeriod") -> int:
        """Periods from this one to `other`. Negative when `other` is earlier."""
        return other.year - self.year

    @classmethod
    def of(cls, year: Optional[int]) -> Optional["FiscalPeriod"]:
        return cls(year) if year is not None else None

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.label


@dataclass(frozen=True)
class RollForwardPeriods:
    """The two periods a roll-forward moves between, and their relationship."""
    historical: Optional[FiscalPeriod] = None
    current: Optional[FiscalPeriod] = None
    expected_gap_years: int = EXPECTED_ROLL_FORWARD_GAP_YEARS

    @property
    def relationship(self) -> PeriodRelationship:
        if self.historical is None or self.current is None:
            return PeriodRelationship.UNKNOWN
        gap = self.historical.gap_to(self.current)
        if gap == self.expected_gap_years:
            return PeriodRelationship.CONSECUTIVE
        if gap > 0:
            return PeriodRelationship.WIDE_GAP
        if gap == 0:
            return PeriodRelationship.SAME_PERIOD
        return PeriodRelationship.INVERTED

    @property
    def satisfies_invariant(self) -> bool:
        """The gating rule: the historical period strictly precedes the current one."""
        return self.relationship in (
            PeriodRelationship.CONSECUTIVE, PeriodRelationship.WIDE_GAP)

    @property
    def gap_years(self) -> Optional[int]:
        if self.historical is None or self.current is None:
            return None
        return self.historical.gap_to(self.current)

    def describe(self) -> str:
        """Plain-language statement of the relationship, with no hardcoded years."""
        relationship = self.relationship
        if relationship == PeriodRelationship.UNKNOWN:
            return "The periods being rolled between are not both known yet."
        gap = self.gap_years or 0
        if relationship == PeriodRelationship.CONSECUTIVE:
            return (f"{self.historical.label} rolls forward to {self.current.label}, "
                    f"the period immediately after it.")
        if relationship == PeriodRelationship.WIDE_GAP:
            return (f"{self.historical.label} is {gap} periods before {self.current.label}; "
                    f"a roll-forward normally advances "
                    f"{self.expected_gap_years} period(s).")
        if relationship == PeriodRelationship.SAME_PERIOD:
            return (f"Both sides cover {self.current.label}; a roll-forward needs two "
                    f"different periods.")
        return (f"{self.historical.label} is later than {self.current.label}; a roll-forward "
                f"moves forward, not back.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "historical_period": self.historical.label if self.historical else None,
            "current_period": self.current.label if self.current else None,
            "historical_fiscal_year": self.historical.year if self.historical else None,
            "target_fiscal_year": self.current.year if self.current else None,
            "expected_gap_years": self.expected_gap_years,
            "gap_years": self.gap_years,
            "relationship": self.relationship.value,
            "satisfies_invariant": self.satisfies_invariant,
            "statement": self.describe(),
        }


@dataclass
class DocumentSignals:
    """Deterministic, content-derived facts about one artifact."""
    artifact_format: ArtifactFormat
    fiscal_year: Optional[int]
    fiscal_year_hits: int
    placeholder_hits: int
    observed_roles: Tuple[DatasetRole, ...]
    satisfying_roles: Tuple[DatasetRole, ...]
    is_local_file_shaped: bool
    is_blank_template_shaped: bool
    record_count: int

    @property
    def supplies_current_year_data(self) -> bool:
        return bool(self.satisfying_roles)

    def detected_label(self) -> str:
        """Plain-language description of what the file actually is."""
        if self.is_blank_template_shaped and self.is_local_file_shaped:
            return "Blank Local File template"
        if self.is_local_file_shaped:
            return (f"FY{self.fiscal_year} Final Local File" if self.fiscal_year
                    else "Local File document")
        if self.supplies_current_year_data:
            return (f"FY{self.fiscal_year} source data" if self.fiscal_year
                    else "Source data file")
        if self.is_blank_template_shaped:
            return "Blank template"
        return "Unrecognised document"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "format": self.artifact_format.value,
            "fiscal_year": self.fiscal_year,
            "fiscal_year_hits": self.fiscal_year_hits,
            "placeholder_hits": self.placeholder_hits,
            "is_local_file_shaped": self.is_local_file_shaped,
            "is_blank_template_shaped": self.is_blank_template_shaped,
            "supplies_current_year_data": self.supplies_current_year_data,
            "record_count": self.record_count,
            "detected_label": self.detected_label(),
            # Carried so a reloaded session keeps the profile it already paid for
            # and never has to re-open the file to answer a readiness question.
            "observed_roles": [r.value for r in self.observed_roles],
            "satisfying_roles": [r.value for r in self.satisfying_roles],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentSignals":
        return cls(
            artifact_format=ArtifactFormat(data.get("format", ArtifactFormat.UNSUPPORTED.value)),
            fiscal_year=data.get("fiscal_year"),
            fiscal_year_hits=int(data.get("fiscal_year_hits", 0)),
            placeholder_hits=int(data.get("placeholder_hits", 0)),
            observed_roles=tuple(DatasetRole(r) for r in data.get("observed_roles", [])),
            satisfying_roles=tuple(DatasetRole(r) for r in data.get("satisfying_roles", [])),
            is_local_file_shaped=bool(data.get("is_local_file_shaped", False)),
            is_blank_template_shaped=bool(data.get("is_blank_template_shaped", False)),
            record_count=int(data.get("record_count", 0)),
        )


class SignalExtractor:
    """Reads content signals out of an artifact. No filename is ever consulted."""

    @staticmethod
    def corpus_for(path: Path, fmt: ArtifactFormat, scope: SupplyScope) -> EvidenceCorpus:
        if fmt == ArtifactFormat.XLSX:
            return CorpusBuilder.from_workbook(path, scope)
        if fmt == ArtifactFormat.DOCX:
            return CorpusBuilder.from_document(path, scope)
        if fmt == ArtifactFormat.CSV:
            import csv

            rows: List[List[str]] = []
            with open(path, newline="", encoding="utf-8", errors="replace") as handle:
                for i, row in enumerate(csv.reader(handle)):
                    if i >= 500:
                        break
                    rows.append(row)
            return CorpusBuilder.from_rows(path.name, scope, rows, location=path.name)
        raise WorkflowIntakeError(f"No corpus builder for format {fmt.value}")

    @classmethod
    def extract(cls, path: Path, artifact: SourceArtifact,
                scope: SupplyScope) -> DocumentSignals:
        fmt = artifact.format
        if fmt == ArtifactFormat.UNSUPPORTED:
            return DocumentSignals(
                artifact_format=fmt, fiscal_year=None, fiscal_year_hits=0,
                placeholder_hits=0, observed_roles=(), satisfying_roles=(),
                is_local_file_shaped=False, is_blank_template_shaped=False,
                record_count=0,
            )

        corpus = cls.corpus_for(path, fmt, scope)
        blob = "\n".join(row.joined() for row in corpus.rows)

        period_counts = Counter(int(y) for y in _PERIOD_PATTERN.findall(blob))
        fiscal_year, hits = None, 0
        if period_counts:
            fiscal_year, hits = period_counts.most_common(1)[0]
            if hits < MIN_PERIOD_HITS:
                fiscal_year = None

        placeholder_hits = len(_PLACEHOLDER_PATTERN.findall(blob))
        observed = tuple(artifact.dataset_roles)
        satisfying = tuple(artifact.satisfying_roles)

        is_local_file_shaped = (
            fmt == ArtifactFormat.DOCX
            and _LOCAL_FILE_SHAPE_ROLES.issubset(set(observed))
        )
        is_blank_template_shaped = (
            placeholder_hits >= MIN_PLACEHOLDER_HITS and fiscal_year is None
        )

        return DocumentSignals(
            artifact_format=fmt,
            fiscal_year=fiscal_year,
            fiscal_year_hits=hits,
            placeholder_hits=placeholder_hits,
            observed_roles=observed,
            satisfying_roles=satisfying,
            is_local_file_shaped=is_local_file_shaped,
            is_blank_template_shaped=is_blank_template_shaped,
            record_count=corpus.record_count,
        )


# ============================================================================
# 5. SLOT ASSIGNMENT
# ============================================================================

@dataclass
class SlotAssignment:
    """One document assigned to one slot, with its content verdict."""
    document_id: str
    slot_id: SlotId
    filename: str
    file_format: str
    file_hash: str
    file_size: int = 0
    perception_status: str = "ready"
    element_count: Optional[int] = None
    artifact_id: Optional[str] = None
    validation_status: SlotValidationStatus = SlotValidationStatus.PENDING
    detected_label: str = ""
    expected_label: str = ""
    reasons: List[str] = field(default_factory=list)
    signals: Optional[DocumentSignals] = None
    human_review_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    assigned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_usable(self) -> bool:
        """Counts as 'present' for the execution gate."""
        if self.validation_status == SlotValidationStatus.ROLE_CONFIRMED:
            return True
        return (self.validation_status == SlotValidationStatus.HUMAN_REVIEW
                and self.human_review_acknowledged)

    @property
    def version_label(self) -> str:
        """Short content version shown in the panel — the file's own hash."""
        return self.file_hash[:12] if self.file_hash else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "slot_id": self.slot_id.value,
            "filename": self.filename,
            "format": self.file_format,
            "file_hash": self.file_hash,
            "version_label": self.version_label,
            "file_size": self.file_size,
            "perception_status": self.perception_status,
            "element_count": self.element_count,
            "artifact_id": self.artifact_id,
            "validation_status": self.validation_status.value,
            "detected_label": self.detected_label,
            "expected_label": self.expected_label,
            "reasons": list(self.reasons),
            "human_review_acknowledged": self.human_review_acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "assigned_at": self.assigned_at,
            "signals": self.signals.to_dict() if self.signals else None,
            "is_usable": self.is_usable,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlotAssignment":
        signals = data.get("signals")
        return cls(
            document_id=data["document_id"],
            slot_id=SlotId(data["slot_id"]),
            filename=data.get("filename", ""),
            file_format=data.get("format", ""),
            file_hash=data.get("file_hash", ""),
            file_size=int(data.get("file_size", 0)),
            perception_status=data.get("perception_status", "ready"),
            element_count=data.get("element_count"),
            artifact_id=data.get("artifact_id"),
            validation_status=SlotValidationStatus(
                data.get("validation_status", SlotValidationStatus.PENDING.value)),
            detected_label=data.get("detected_label", ""),
            expected_label=data.get("expected_label", ""),
            reasons=list(data.get("reasons", [])),
            signals=DocumentSignals.from_dict(signals) if signals else None,
            human_review_acknowledged=bool(data.get("human_review_acknowledged", False)),
            acknowledged_by=data.get("acknowledged_by"),
            assigned_at=data.get("assigned_at", datetime.now(timezone.utc).isoformat()),
        )


# ============================================================================
# 6. SLOT ROLE VALIDATION
# ============================================================================

@dataclass(frozen=True)
class SlotVerdict:
    status: SlotValidationStatus
    detected_label: str
    expected_label: str
    reasons: Tuple[str, ...]


class SlotRoleValidator:
    """Decides whether a file's CONTENT matches the slot it was dropped into.

    Every branch is deterministic and derived from DocumentSignals. Nothing here
    reads a filename, and nothing here silently accepts a contradiction.
    """

    @classmethod
    def validate(
        cls,
        spec: InputSlotSpec,
        signals: DocumentSignals,
        periods: Optional[RollForwardPeriods] = None,
    ) -> SlotVerdict:
        """Judge one file against one slot.

        `periods` carries the surrounding evidence: which period the current-year
        sources state, and which period an accepted historical file states. Both
        come from document content, so no year is ever hardcoded here.
        """
        periods = periods or RollForwardPeriods()
        expected = spec.expected_label
        detected = signals.detected_label()

        if signals.artifact_format not in spec.accepted_formats:
            accepted = ", ".join(f".{f.value.lower()}" for f in spec.accepted_formats)
            return SlotVerdict(
                SlotValidationStatus.FORMAT_REJECTED, detected, expected,
                (f"{spec.display_name} accepts {accepted}. "
                 f"This file is .{signals.artifact_format.value.lower()}.",),
            )

        if spec.slot_id == SlotId.HISTORICAL_LOCAL_FILE:
            return cls._validate_historical(spec, signals, detected, expected, periods)
        if spec.slot_id == SlotId.MASTER_TEMPLATE:
            return cls._validate_template(spec, signals, detected, expected)
        return cls._validate_current_source(spec, signals, detected, expected, periods)

    # -- per-slot rules -------------------------------------------------

    @staticmethod
    def _validate_historical(spec, signals, detected, expected,
                             periods: RollForwardPeriods) -> SlotVerdict:
        if not signals.is_local_file_shaped:
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                ("This file does not read as a Local File: it carries neither a "
                 "functional analysis nor a business narrative.",),
            )
        if signals.is_blank_template_shaped:
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                (f"This is an unfilled template ({signals.placeholder_hits} unresolved "
                 f"placeholders) with no fiscal period stated. The historical slot needs "
                 f"the completed Local File for the period being rolled forward FROM.",),
            )

        candidate = FiscalPeriod.of(signals.fiscal_year)
        if candidate is None:
            return SlotVerdict(
                SlotValidationStatus.HUMAN_REVIEW, detected, expected,
                ("The fiscal period this Local File covers could not be determined from "
                 "its content, so it cannot be confirmed as the preceding period.",),
            )

        # Judge this candidate as the historical side against whatever period the
        # current-year sources state. Both sides are read from content.
        relation = RollForwardPeriods(
            historical=candidate, current=periods.current,
            expected_gap_years=periods.expected_gap_years)

        if relation.relationship == PeriodRelationship.UNKNOWN:
            return SlotVerdict(
                SlotValidationStatus.ROLE_CONFIRMED, detected, expected,
                (f"Content states {candidate.label}; the period is re-checked when "
                 f"current-year sources arrive.",),
            )
        if relation.relationship in (PeriodRelationship.SAME_PERIOD,
                                     PeriodRelationship.INVERTED):
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                (relation.describe(),
                 f"The historical slot needs the Local File for the period being rolled "
                 f"forward FROM, not {candidate.label}."),
            )
        if relation.relationship == PeriodRelationship.WIDE_GAP:
            return SlotVerdict(
                SlotValidationStatus.HUMAN_REVIEW, detected, expected,
                (relation.describe(),
                 "Confirm this is the Local File you mean to roll forward."),
            )
        return SlotVerdict(
            SlotValidationStatus.ROLE_CONFIRMED, detected, expected,
            (f"Content states {candidate.label}. {relation.describe()}",),
        )

    @staticmethod
    def _validate_template(spec, signals, detected, expected) -> SlotVerdict:
        if not signals.is_local_file_shaped:
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                ("This file does not carry the section structure of a Local File template.",),
            )
        if signals.fiscal_year is not None:
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                (f"This is a completed Local File for FY{signals.fiscal_year}, not a blank "
                 f"master template.",),
            )
        if not signals.is_blank_template_shaped:
            return SlotVerdict(
                SlotValidationStatus.HUMAN_REVIEW, detected, expected,
                ("No fiscal period and too few unfilled placeholders to confirm this is the "
                 "blank master template.",),
            )
        return SlotVerdict(
            SlotValidationStatus.ROLE_CONFIRMED, detected, expected,
            (f"Blank template structure with {signals.placeholder_hits} unresolved "
             f"placeholders and no stated fiscal period.",),
        )

    @staticmethod
    def _validate_current_source(spec, signals, detected, expected,
                                 periods: RollForwardPeriods) -> SlotVerdict:
        if signals.is_local_file_shaped:
            return SlotVerdict(
                SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                ("This is a Local File document, not current-year source data. Local Files "
                 "belong in the Previous Local File or Master Template slot.",),
            )
        if not signals.supplies_current_year_data:
            return SlotVerdict(
                SlotValidationStatus.HUMAN_REVIEW, detected, expected,
                ("No complete current-year dataset was recognised in this file, so it "
                 "cannot be confirmed as a source.",),
            )

        candidate = FiscalPeriod.of(signals.fiscal_year)
        if candidate is not None and periods.historical is not None:
            # This source is the current side; the accepted historical file is the
            # other. A source that does not post-date it cannot be current-year data.
            relation = RollForwardPeriods(
                historical=periods.historical, current=candidate,
                expected_gap_years=periods.expected_gap_years)
            if not relation.satisfies_invariant:
                return SlotVerdict(
                    SlotValidationStatus.ROLE_MISMATCH, detected, expected,
                    (f"This source states {candidate.label}, which is not later than the "
                     f"{periods.historical.label} Local File being rolled forward.",),
                )

        supplied = len(signals.satisfying_roles)
        period = f"{candidate.label} " if candidate else ""
        return SlotVerdict(
            SlotValidationStatus.ROLE_CONFIRMED, detected, expected,
            (f"{period}source data with {supplied} complete dataset(s) "
             f"across {signals.record_count} records.".strip(),),
        )


# ============================================================================
# 7. READINESS SUMMARY
# ============================================================================

@dataclass
class DomainReadiness:
    domain_id: str
    display_name: str
    status: DomainStatus
    detail: str
    supplied_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "display_name": self.display_name,
            "status": self.status.value,
            "status_label": DOMAIN_STATUS_LABEL[self.status],
            "detail": self.detail,
            "supplied_by": list(self.supplied_by),
        }


# ============================================================================
# 8. WORKFLOW INTAKE SESSION
# ============================================================================

@dataclass
class InputSlotState:
    """The typed InputSlot contract, as the API and UI consume it."""
    spec: InputSlotSpec
    assignments: List[SlotAssignment] = field(default_factory=list)

    @property
    def assigned_document_ids(self) -> List[str]:
        return [a.document_id for a in self.assignments]

    @property
    def validation_status(self) -> SlotValidationStatus:
        """The slot's worst assignment verdict — problems are never averaged away."""
        if not self.assignments:
            return SlotValidationStatus.PENDING
        order = [
            SlotValidationStatus.FORMAT_REJECTED,
            SlotValidationStatus.ROLE_MISMATCH,
            SlotValidationStatus.HUMAN_REVIEW,
            SlotValidationStatus.PENDING,
            SlotValidationStatus.ROLE_CONFIRMED,
        ]
        for status in order:
            if any(a.validation_status == status for a in self.assignments):
                return status
        return SlotValidationStatus.PENDING

    @property
    def readiness_status(self) -> SlotReadinessStatus:
        if not self.assignments:
            return SlotReadinessStatus.EMPTY
        usable = [a for a in self.assignments if a.is_usable]
        if not usable:
            return SlotReadinessStatus.BLOCKED
        if len(usable) < len(self.assignments):
            return SlotReadinessStatus.NEEDS_REVIEW
        if any(a.validation_status == SlotValidationStatus.HUMAN_REVIEW for a in usable):
            return SlotReadinessStatus.NEEDS_REVIEW
        if (self.spec.cardinality == Cardinality.EXACTLY_ONE and len(usable) != 1):
            return SlotReadinessStatus.NEEDS_REVIEW
        return SlotReadinessStatus.SATISFIED

    @property
    def is_satisfied(self) -> bool:
        return self.readiness_status in (
            SlotReadinessStatus.SATISFIED, SlotReadinessStatus.NEEDS_REVIEW)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.spec.slot_id.value,
            "display_name": self.spec.display_name,
            "section_title": self.spec.section_title,
            "description": self.spec.description,
            "required": self.spec.required,
            "cardinality": self.spec.cardinality.value,
            "accepts_multiple": self.spec.accepts_multiple,
            "accepted_formats": [f.value for f in self.spec.accepted_formats],
            "add_action_label": self.spec.add_action_label,
            "expected_label": self.spec.expected_label,
            "assigned_document_ids": self.assigned_document_ids,
            "validation_status": self.validation_status.value,
            "readiness_status": self.readiness_status.value,
            "assignments": [a.to_dict() for a in self.assignments],
        }


class WorkflowIntakeSession:
    """The structured intake for one LOCAL_FILE_ROLL_FORWARD workspace.

    Lifecycle per uploaded file:

        assign_document()  -> profile (perceive + classify via the canonical
                              policy engine) -> validate against the slot's role
                              -> re-validate every slot (periods are relative)
                              -> recalculate readiness through SourceRegistry

    Readiness is only ever produced by ReadinessRecalculator, so this class
    cannot invent a readiness value the governance layer forbids.
    """

    TOTAL_STEPS = 4
    STEP_LABELS = {
        1: "Input Documents",
        2: "Review Plan",
        3: "Execute Roll-Forward",
        4: "Review Output",
    }

    def __init__(
        self,
        session_id: str,
        workflow_type: WorkflowType = WorkflowType.LOCAL_FILE_ROLL_FORWARD,
        target_fiscal_year: Optional[int] = None,
        workflow_id: Optional[str] = None,
        user_id: str = "anonymous",
    ):
        self.session_id = session_id
        self.workflow_id = workflow_id or f"wf-{uuid.uuid4().hex[:16]}"
        self.user_id = user_id
        self.workflow_type = workflow_type
        self.target_fiscal_year = target_fiscal_year
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.slots: Dict[SlotId, InputSlotState] = {
            slot_id: InputSlotState(spec=SLOT_SPECS[slot_id]) for slot_id in SLOT_ORDER
        }
        self.registry = SourceRegistry(package_id=f"PKG-{session_id[:8]}")

    # -- lookup ---------------------------------------------------------

    def slot(self, slot_id: SlotId) -> InputSlotState:
        return self.slots[slot_id]

    def find_assignment(self, document_id: str) -> Optional[Tuple[SlotId, SlotAssignment]]:
        for slot_id, state in self.slots.items():
            for assignment in state.assignments:
                if assignment.document_id == document_id:
                    return slot_id, assignment
        return None

    # -- periods --------------------------------------------------------

    @property
    def current_year(self) -> Optional[int]:
        """The current period, taken from the current-year sources' own content."""
        if self.target_fiscal_year is not None:
            return self.target_fiscal_year
        years = [
            a.signals.fiscal_year
            for a in self.slots[SlotId.CURRENT_YEAR_SOURCES].assignments
            if a.signals and a.signals.fiscal_year is not None
        ]
        return max(years) if years else None

    @property
    def periods(self) -> RollForwardPeriods:
        """The two periods this roll-forward moves between, and their relationship.

        Both are read from document content (or, for the current side, from an
        explicitly supplied target period). No year is special-cased anywhere.
        """
        return RollForwardPeriods(
            historical=FiscalPeriod.of(self.historical_year),
            current=FiscalPeriod.of(self.current_year),
        )

    @property
    def historical_year(self) -> Optional[int]:
        for a in self.slots[SlotId.HISTORICAL_LOCAL_FILE].assignments:
            if a.signals and a.signals.fiscal_year is not None:
                return a.signals.fiscal_year
        return None

    # -- assignment -----------------------------------------------------

    def assign_document(
        self,
        slot_id: SlotId,
        document_id: str,
        path: Path,
        filename: str,
        perception_status: str = "ready",
        element_count: Optional[int] = None,
        actor: str = "user",
    ) -> SlotAssignment:
        """Profile one uploaded document and place it in a slot.

        The file must already exist as a perceived document; this method adds a
        workflow ROLE on top of it. It mutates nothing on disk.
        """
        spec = self.slots[slot_id].spec
        existing = self.find_assignment(document_id)
        if existing is not None:
            self.remove_document(existing[0], document_id)

        if (spec.cardinality == Cardinality.EXACTLY_ONE
                and self.slots[slot_id].assignments):
            # A single-file slot replaces rather than accumulates.
            for prior in list(self.slots[slot_id].assignments):
                self.remove_document(slot_id, prior.document_id)

        fmt = EXTENSION_FORMAT.get(Path(filename).suffix.lower(), ArtifactFormat.UNSUPPORTED)
        assignment = SlotAssignment(
            document_id=document_id,
            slot_id=slot_id,
            filename=filename,
            file_format=fmt.value.lower(),
            file_hash="",
            perception_status=perception_status,
            element_count=element_count,
            expected_label=spec.expected_label,
        )

        if fmt not in spec.accepted_formats:
            # Rejected on format alone — never profiled, never registered.
            assignment.file_hash = ""
            assignment.signals = DocumentSignals(
                artifact_format=fmt, fiscal_year=None, fiscal_year_hits=0,
                placeholder_hits=0, observed_roles=(), satisfying_roles=(),
                is_local_file_shaped=False, is_blank_template_shaped=False, record_count=0,
            )
            verdict = SlotRoleValidator.validate(spec, assignment.signals)
            assignment.validation_status = verdict.status
            assignment.detected_label = verdict.detected_label
            assignment.reasons = list(verdict.reasons)
            self.slots[slot_id].assignments.append(assignment)
            return assignment

        artifact = SourceIntakeProfiler.ingest(path, spec.supply_scope)
        assignment.artifact_id = artifact.artifact_id
        assignment.file_hash = artifact.file_hash
        assignment.file_size = artifact.file_size
        assignment.signals = SignalExtractor.extract(path, artifact, spec.supply_scope)

        # Register through the governed registry so the artifact, its hash and
        # its roles enter the audited source package. register() never changes
        # readiness — recalculate_readiness() below is the only path that does.
        self.registry.register(path, spec.supply_scope, actor=actor,
                               artifact_id=artifact.artifact_id)

        self.slots[slot_id].assignments.append(assignment)
        self.revalidate_all()
        self.recalculate_readiness(actor=actor)
        return assignment

    def remove_document(self, slot_id: SlotId, document_id: str) -> bool:
        state = self.slots[slot_id]
        before = len(state.assignments)
        state.assignments = [a for a in state.assignments if a.document_id != document_id]
        removed = len(state.assignments) != before
        if removed:
            self.revalidate_all()
        return removed

    def acknowledge_for_review(self, slot_id: SlotId, document_id: str,
                               actor: str = "user") -> SlotAssignment:
        """Record the explicit human decision to keep a flagged file.

        This is never silent: the decision is stored on the assignment, the file
        keeps its flagged verdict, and every readiness domain it supplies is
        reported as Human review rather than Ready.
        """
        for assignment in self.slots[slot_id].assignments:
            if assignment.document_id != document_id:
                continue
            if assignment.validation_status == SlotValidationStatus.FORMAT_REJECTED:
                raise WorkflowIntakeError(
                    f"'{assignment.filename}' cannot be kept for review: "
                    f"{self.slots[slot_id].spec.display_name} does not accept this file format.")
            assignment.validation_status = SlotValidationStatus.HUMAN_REVIEW
            assignment.human_review_acknowledged = True
            assignment.acknowledged_by = actor
            assignment.reasons = list(assignment.reasons) + [
                "Kept for manual review by the user; the role was not confirmed automatically."
            ]
            return assignment
        raise WorkflowIntakeError(f"Document '{document_id}' is not assigned to {slot_id.value}.")

    def revalidate_all(self) -> None:
        """Re-run every slot verdict.

        Periods are relative: what a historical Local File means depends on what
        the current-year sources say, so an assignment made earlier is re-judged
        whenever the surrounding evidence changes.
        """
        current_period = FiscalPeriod.of(self.current_year)

        def apply(slot_id: SlotId, periods: RollForwardPeriods) -> None:
            state = self.slots[slot_id]
            for assignment in state.assignments:
                if assignment.signals is None:
                    continue
                if assignment.human_review_acknowledged:
                    continue  # an explicit human decision is not overwritten
                verdict = SlotRoleValidator.validate(state.spec, assignment.signals, periods)
                assignment.validation_status = verdict.status
                assignment.detected_label = verdict.detected_label
                assignment.expected_label = verdict.expected_label
                assignment.reasons = list(verdict.reasons)

        # Pass 1 — the baseline slots. The historical candidate is judged against
        # the period the current-year sources state.
        against_current = RollForwardPeriods(current=current_period)
        apply(SlotId.HISTORICAL_LOCAL_FILE, against_current)
        apply(SlotId.MASTER_TEMPLATE, against_current)

        # Pass 2 — the sources are only measured against a historical file that
        # was itself accepted. A rejected historical file is one problem; it must
        # not cascade into accusing every valid source of being stale.
        # Only a file whose role was CONFIRMED sets the period the sources are
        # measured against. A rejected historical file is one problem, and a file
        # the user knowingly kept for review is their decision — neither should
        # cascade into accusing valid current-year sources of being stale.
        confirmed_historical = next(
            (FiscalPeriod.of(a.signals.fiscal_year)
             for a in self.slots[SlotId.HISTORICAL_LOCAL_FILE].assignments
             if a.validation_status == SlotValidationStatus.ROLE_CONFIRMED
             and a.signals and a.signals.fiscal_year is not None),
            None,
        )
        apply(SlotId.CURRENT_YEAR_SOURCES,
              RollForwardPeriods(historical=confirmed_historical, current=current_period))

    # -- readiness ------------------------------------------------------

    def recalculate_readiness(self, actor: str = "system") -> Dict[str, int]:
        """Delegates to the governed recalculation path and returns the counts."""
        _event, _transitions, counts = self.registry.recalculate_readiness(
            _domain_regions(),
            role_alias=_domain_role_alias(),
            actor=actor,
        )
        return counts

    def _governed_domain_readiness(self) -> Dict[str, str]:
        """Domain readiness as ReadinessRecalculator computes it.

        Derived from the roles the usable current-year sources actually satisfy,
        so it survives a reload of the persisted intake state without depending
        on the in-memory audit package.
        """
        available: Set[str] = set()
        for assignment in self.slots[SlotId.CURRENT_YEAR_SOURCES].assignments:
            if assignment.is_usable and assignment.signals is not None:
                available |= {r.value for r in assignment.signals.satisfying_roles}
        regions = _domain_regions()
        transitions, _counts = ReadinessRecalculator.simulate(
            regions, available, role_alias=_domain_role_alias())
        recalculated = {r["region_id"]: r.get("readiness", "") for r in regions}
        for transition in transitions:
            recalculated[transition.region_id] = transition.recalculated
        return recalculated

    def readiness_summary(self) -> List[DomainReadiness]:
        """One row per source domain, in plain language."""
        source_slot = self.slots[SlotId.CURRENT_YEAR_SOURCES]
        usable = [a for a in source_slot.assignments
                  if a.is_usable and a.signals is not None]
        flagged = {a.document_id for a in usable
                   if a.validation_status == SlotValidationStatus.HUMAN_REVIEW}
        has_sources = bool(source_slot.assignments)

        recalculated = self._governed_domain_readiness()
        rows: List[DomainReadiness] = []

        for domain in SOURCE_DOMAINS:
            wanted = set(domain.roles)
            suppliers = [a for a in usable if wanted & set(a.signals.satisfying_roles)]
            observers = [a for a in usable if wanted & set(a.signals.observed_roles)]

            if suppliers:
                only_flagged = all(a.document_id in flagged for a in suppliers)
                status = DomainStatus.HUMAN_REVIEW if only_flagged else DomainStatus.SUPPORTED
                names = [a.filename for a in suppliers]
                detail = (
                    "Supplied by a file kept for manual review."
                    if only_flagged else
                    f"Supplied by {', '.join(names)}."
                )
            elif not has_sources:
                status = DomainStatus.MISSING_SOURCE
                detail = domain.missing_hint
                names = []
            elif observers:
                # Mentioned, but not with every figure the domain needs. That is
                # blocked, not supported: partial evidence never becomes Ready.
                status = DomainStatus.BLOCKED
                detail = ("Mentioned in the uploaded sources, but the required figures are "
                          "incomplete. " + domain.missing_hint)
                names = []
            else:
                status = DomainStatus.BLOCKED
                detail = domain.missing_hint
                names = []

            # The governed recalculation is the authority on "supported": if it
            # did not lift the domain out of BLOCKED, this row cannot claim Ready.
            if (status == DomainStatus.SUPPORTED
                    and recalculated.get(domain.domain_id, "").startswith("BLOCKED")):
                status = DomainStatus.HUMAN_REVIEW
                detail = "Evidence found, pending confirmation."

            rows.append(DomainReadiness(
                domain_id=domain.domain_id, display_name=domain.display_name,
                status=status, detail=detail, supplied_by=names,
            ))
        return rows

    # -- gating ---------------------------------------------------------

    def execution_gate(self) -> Dict[str, Any]:
        """Roll-forward stays blocked until every required slot holds a usable file."""
        missing: List[str] = []
        blocked: List[str] = []
        for slot_id in SLOT_ORDER:
            state = self.slots[slot_id]
            if not state.spec.required:
                continue
            readiness = state.readiness_status
            if readiness == SlotReadinessStatus.EMPTY:
                missing.append(state.spec.display_name)
            elif readiness == SlotReadinessStatus.BLOCKED:
                blocked.append(state.spec.display_name)

        allowed = not missing and not blocked
        if blocked:
            first_blocked = blocked[0]
            slot_state = next(st for st in self.slots.values()
                              if st.spec.display_name == first_blocked)
            message = (
                f"Replace the file in {first_blocked} — its format is not accepted."
                if slot_state.validation_status == SlotValidationStatus.FORMAT_REJECTED
                else f"Resolve the file role mismatch in {first_blocked} to continue."
            )
        elif missing:
            first = missing[0]
            message = (f"Upload at least one {first} file to continue."
                       if first == SLOT_SPECS[SlotId.CURRENT_YEAR_SOURCES].display_name
                       else f"Upload {first} to continue.")
        else:
            message = "All required inputs are present. Roll-forward can be planned."

        return {
            "execution_allowed": allowed,
            "plan_approval_allowed": allowed,
            "mutation_allowed": False,
            "message": message,
            "missing_slots": missing,
            "blocked_slots": blocked,
            "statement": (
                "Intake gating only. No plan is approved, no document is mutated and no "
                "output is produced by this phase."
            ),
        }

    # -- agent context --------------------------------------------------

    def agent_workflow_context(self) -> Dict[str, Any]:
        """The structured context the Agent receives — ids and roles, never filenames.

        The Agent is told WHICH document plays WHICH role. It never has to infer
        the workflow, and it never has to read a filename to find the template.
        """
        historical = self.slots[SlotId.HISTORICAL_LOCAL_FILE].assignments
        sources = self.slots[SlotId.CURRENT_YEAR_SOURCES].assignments
        template = self.slots[SlotId.MASTER_TEMPLATE].assignments

        def usable_ids(items: Sequence[SlotAssignment]) -> List[str]:
            return [a.document_id for a in items if a.is_usable]

        historical_ids = usable_ids(historical)
        template_ids = usable_ids(template)
        gate = self.execution_gate()

        return {
            "workflow": self.workflow_type.value,
            "historical_document_id": historical_ids[0] if historical_ids else None,
            "current_source_document_ids": usable_ids(sources),
            "template_document_id": template_ids[0] if template_ids else None,
            "target_fiscal_year": self.current_year,
            "historical_fiscal_year": self.historical_year,
            "periods": self.periods.to_dict(),
            "inputs_complete": gate["execution_allowed"],
            "execution_allowed": gate["execution_allowed"],
            "readiness": [row.to_dict() for row in self.readiness_summary()],
        }

    # -- serialisation --------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "workflow": self.workflow_type.value,
            "workflow_display_name": "Local File Roll-Forward",
            "created_at": self.created_at,
            "target_fiscal_year": self.target_fiscal_year,
            "periods": self.periods.to_dict(),
            "step": 1,
            "total_steps": self.TOTAL_STEPS,
            "step_label": self.STEP_LABELS[1],
            "slots": [self.slots[slot_id].to_dict() for slot_id in SLOT_ORDER],
            "readiness": [row.to_dict() for row in self.readiness_summary()],
            "gate": self.execution_gate(),
            "agent_context": self.agent_workflow_context(),
        }

    def state_to_dict(self) -> Dict[str, Any]:
        """Minimal serialised form — assignments only; verdicts are recomputed."""
        return {
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "workflow": self.workflow_type.value,
            "created_at": self.created_at,
            "target_fiscal_year": self.target_fiscal_year,
            "assignments": [
                a.to_dict()
                for slot_id in SLOT_ORDER
                for a in self.slots[slot_id].assignments
            ],
        }

    @classmethod
    def from_state_dict(cls, data: Dict[str, Any]) -> "WorkflowIntakeSession":
        session = cls(
            session_id=data["session_id"],
            workflow_type=WorkflowType(data.get("workflow", WorkflowType.LOCAL_FILE_ROLL_FORWARD.value)),
            target_fiscal_year=data.get("target_fiscal_year"),
            workflow_id=data.get("workflow_id"),
            user_id=data.get("user_id", "anonymous"),
        )
        session.created_at = data.get("created_at", session.created_at)
        for raw in data.get("assignments", []):
            assignment = SlotAssignment.from_dict(raw)
            session.slots[assignment.slot_id].assignments.append(assignment)
        session.revalidate_all()
        return session

    # -- repository records ---------------------------------------------
    #
    # The canonical home of this state is the workflow repository (Postgres in
    # production). These two methods are the only bridge between the domain
    # objects and those rows; nothing else knows how the state is stored.

    def to_records(self) -> Tuple["WorkflowRecord", List["WorkflowSlotAssignmentRecord"]]:
        from adapters.repository import WorkflowRecord, WorkflowSlotAssignmentRecord

        workflow = WorkflowRecord(
            workflow_id=self.workflow_id,
            session_id=self.session_id,
            user_id=self.user_id,
            workflow_type=self.workflow_type.value,
            target_fiscal_year=self.target_fiscal_year,
            created_at=self.created_at,
        )

        rows: List[WorkflowSlotAssignmentRecord] = []
        for slot_id in SLOT_ORDER:
            state = self.slots[slot_id]
            readiness = state.readiness_status.value
            for assignment in state.assignments:
                rows.append(WorkflowSlotAssignmentRecord(
                    workflow_id=self.workflow_id,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    slot_id=slot_id.value,
                    document_id=assignment.document_id,
                    filename=assignment.filename,
                    file_format=assignment.file_format,
                    file_hash=assignment.file_hash,
                    file_size=assignment.file_size,
                    perception_status=assignment.perception_status,
                    element_count=assignment.element_count,
                    artifact_id=assignment.artifact_id,
                    validation_status=assignment.validation_status.value,
                    readiness_status=readiness,
                    detected_label=assignment.detected_label,
                    expected_label=assignment.expected_label,
                    reasons=list(assignment.reasons),
                    signals=assignment.signals.to_dict() if assignment.signals else {},
                    human_review_acknowledged=assignment.human_review_acknowledged,
                    acknowledged_by=assignment.acknowledged_by,
                    created_at=assignment.assigned_at,
                ))
        return workflow, rows

    @classmethod
    def from_records(cls, workflow: "WorkflowRecord",
                     assignments: Sequence["WorkflowSlotAssignmentRecord"]
                     ) -> "WorkflowIntakeSession":
        session = cls(
            session_id=workflow.session_id,
            workflow_type=WorkflowType(workflow.workflow_type),
            target_fiscal_year=workflow.target_fiscal_year,
            workflow_id=workflow.workflow_id,
            user_id=workflow.user_id,
        )
        session.created_at = workflow.created_at
        for row in assignments:
            slot_id = SlotId(row.slot_id)
            session.slots[slot_id].assignments.append(SlotAssignment(
                document_id=row.document_id,
                slot_id=slot_id,
                filename=row.filename,
                file_format=row.file_format,
                file_hash=row.file_hash,
                file_size=row.file_size,
                perception_status=row.perception_status,
                element_count=row.element_count,
                artifact_id=row.artifact_id,
                validation_status=SlotValidationStatus(row.validation_status),
                detected_label=row.detected_label,
                expected_label=row.expected_label,
                reasons=list(row.reasons or []),
                signals=DocumentSignals.from_dict(row.signals) if row.signals else None,
                human_review_acknowledged=row.human_review_acknowledged,
                acknowledged_by=row.acknowledged_by,
                assigned_at=row.created_at,
            ))
        # Verdicts are always recomputed from the stored content profile, never
        # trusted from the row: a stored verdict could otherwise outlive the rule
        # that produced it.
        session.revalidate_all()
        return session


__all__ = [
    "WorkflowType",
    "SlotId",
    "Cardinality",
    "SlotValidationStatus",
    "SlotReadinessStatus",
    "DomainStatus",
    "DOMAIN_STATUS_LABEL",
    "WorkflowIntakeError",
    "InputSlotSpec",
    "SLOT_SPECS",
    "SLOT_ORDER",
    "SourceDomain",
    "SOURCE_DOMAINS",
    "DocumentSignals",
    "SignalExtractor",
    "SlotAssignment",
    "SlotVerdict",
    "SlotRoleValidator",
    "DomainReadiness",
    "InputSlotState",
    "WorkflowIntakeSession",
    "FiscalPeriod",
    "RollForwardPeriods",
    "PeriodRelationship",
    "EXPECTED_ROLL_FORWARD_GAP_YEARS",
]

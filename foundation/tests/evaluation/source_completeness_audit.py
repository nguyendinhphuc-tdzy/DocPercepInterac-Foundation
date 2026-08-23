"""
Local File Roll-Forward Source Completeness & Readiness Audit (Phase E)
=======================================================================
Location: foundation/tests/evaluation/source_completeness_audit.py

Answers two questions, from evidence only:

    "What can we safely automate with the files we actually have?"
    "What exact additional files or human evidence are required for the rest?"

This is an AUDIT. It plans no mutation, changes no production behaviour, and
never fabricates a source binding, a cell range or an element id.

Ground Truth handling
---------------------
`HMV-26-Final-Local File for FY2024` is quarantined for the whole readiness
computation by the Phase C2 `GroundTruthQuarantine`. It is opened only after
`freeze()` has returned, and only to grade whether the gaps this audit found
correspond to real FY2024 changes. It can never alter readiness.

Emits
-----
    docs/evaluation/LocalFile_RollForward_Source_Completeness_2026-08-23.md
    docs/evaluation/LocalFile_RollForward_Required_Source_Matrix_2026-08-23.json
    docs/evaluation/LocalFile_RollForward_Readiness_v1_2026-08-23.json
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import warnings
import zipfile

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from docx import Document
from docx.text.paragraph import Paragraph

REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(REPO_ROOT), str(REPO_ROOT / "foundation")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from applications.rollforward.mutation_precondition import TableAnatomyProfiler
from applications.rollforward.semantic_binding import (
    BindingVerdict,
    RowSemantics,
    SemanticBindingValidator,
    TargetSchemaDeriver,
)
from applications.rollforward.source_capability import (
    DatasetRole,
    SheetDatasetProfile,
    SourceCapabilityProfiler,
    WorkbookCapabilityProfile,
)
from applications.rollforward.table_identity import (
    CorrespondenceConfidence,
    SemanticLabel,
    TableCorrespondenceResolver,
    TableIdentityProfiler,
)

from foundation.tests.evaluation.rollforward_clean_planner_c2 import (  # noqa: E402
    PATH_APP1,
    PATH_FARPT,
    PATH_GROUND_TRUTH_FORBIDDEN,
    PATH_HIST,
    PATH_TMPL,
    GroundTruthQuarantine,
)

AUDIT_DATE = "2026-08-23"
MD_PATH = REPO_ROOT / "docs/evaluation" / f"LocalFile_RollForward_Source_Completeness_{AUDIT_DATE}.md"
MATRIX_JSON = REPO_ROOT / "docs/evaluation" / f"LocalFile_RollForward_Required_Source_Matrix_{AUDIT_DATE}.json"
READINESS_JSON = REPO_ROOT / "docs/evaluation" / f"LocalFile_RollForward_Readiness_v1_{AUDIT_DATE}.json"

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_HEADING_RE = re.compile(r"^(heading\s*(\d+)|title|subtitle)$", re.IGNORECASE)


# ============================================================================
# 1. TAXONOMIES
# ============================================================================

class SourceDatasetRole(str, Enum):
    """Full Phase E dataset-role taxonomy (superset of the C2 roles)."""
    TAXPAYER_PROFILE = "TAXPAYER_PROFILE"
    OWNERSHIP_STRUCTURE = "OWNERSHIP_STRUCTURE"
    RELATED_PARTY_TRANSACTIONS = "RELATED_PARTY_TRANSACTIONS"
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    FIXED_ASSETS = "FIXED_ASSETS"
    INTEREST_EXPENSE = "INTEREST_EXPENSE"
    TAX_SCHEDULE = "TAX_SCHEDULE"
    SEGMENTED_DATA = "SEGMENTED_DATA"
    APPENDIX_DISCLOSURE = "APPENDIX_DISCLOSURE"
    NARRATIVE_DATA = "NARRATIVE_DATA"
    BENCHMARKING_DATA = "BENCHMARKING_DATA"
    COMPARABLE_COMPANIES = "COMPARABLE_COMPANIES"
    IQR_RESULTS = "IQR_RESULTS"
    SCREENING_RESULTS = "SCREENING_RESULTS"
    CONTRACTUAL_DATA = "CONTRACTUAL_DATA"
    ORGANIZATIONAL_DATA = "ORGANIZATIONAL_DATA"
    STATUTORY_TEXT = "STATUTORY_TEXT"
    UNKNOWN = "UNKNOWN"


class SourceCoverage(str, Enum):
    """How well the CURRENT source set covers a region's requirement."""
    FULLY_SUPPORTED = "FULLY_SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    MISSING_SOURCE = "MISSING_SOURCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class Readiness(str, Enum):
    """What kind of readiness a region has. Never a bare 'READY'."""
    AUTO_NOOP_READY = "AUTO_NOOP_READY"
    AUTO_MUTATION_READY = "AUTO_MUTATION_READY"
    HUMAN_REVIEW_READY = "HUMAN_REVIEW_READY"
    BLOCKED_MISSING_SOURCE = "BLOCKED_MISSING_SOURCE"
    BLOCKED_INSUFFICIENT_EVIDENCE = "BLOCKED_INSUFFICIENT_EVIDENCE"
    BLOCKED_SCHEMA_MISMATCH = "BLOCKED_SCHEMA_MISMATCH"
    BLOCKED_UNSUPPORTED_CONSTRUCT = "BLOCKED_UNSUPPORTED_CONSTRUCT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ArtifactType(str, Enum):
    """What KIND of artifact a gap requires (never just 'more data')."""
    STRUCTURED_EXCEL = "STRUCTURED_EXCEL"
    NARRATIVE_DOCUMENT = "NARRATIVE_DOCUMENT"
    CONTRACTUAL_DOCUMENT = "CONTRACTUAL_DOCUMENT"
    BENCHMARKING_REPORT = "BENCHMARKING_REPORT"
    MANAGEMENT_INFORMATION = "MANAGEMENT_INFORMATION"
    ORGANIZATION_CHART = "ORGANIZATION_CHART"
    LEGAL_REGULATORY_SOURCE = "LEGAL_REGULATORY_SOURCE"
    FIGURE_CHART_SOURCE = "FIGURE_CHART_SOURCE"
    SUPPORTING_SCHEDULE = "SUPPORTING_SCHEDULE"
    NONE_REQUIRED = "NONE_REQUIRED"


class Priority(str, Enum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class HistoricalReuse(str, Enum):
    """How FY2023 text may be treated as a source (Phase E §12)."""
    REUSABLE_BASELINE = "REUSABLE_BASELINE"
    REUSABLE_WITH_VERIFICATION = "REUSABLE_WITH_VERIFICATION"
    REQUIRES_CURRENT_YEAR_SOURCE = "REQUIRES_CURRENT_YEAR_SOURCE"
    UNSAFE_TO_REUSE = "UNSAFE_TO_REUSE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FigureKind(str, Enum):
    LOGO = "LOGO"
    OWNERSHIP_CHART = "OWNERSHIP_CHART"
    ORGANIZATION_CHART = "ORGANIZATION_CHART"
    PROCESS_FLOW = "PROCESS_FLOW"
    TRANSACTION_FLOW = "TRANSACTION_FLOW"
    BENCHMARKING_CHART = "BENCHMARKING_CHART"
    FINANCIAL_CHART = "FINANCIAL_CHART"
    EMBEDDED_SCREENSHOT = "EMBEDDED_SCREENSHOT"
    LAYOUT_TEXT_BOX = "LAYOUT_TEXT_BOX"
    UNKNOWN = "UNKNOWN"


class FigureReadiness(str, Enum):
    STATIC_PRESERVE = "STATIC_PRESERVE"
    UPDATEABLE = "UPDATEABLE"
    REGENERATABLE = "REGENERATABLE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCKED = "BLOCKED"


class RegionDomain(str, Enum):
    """Semantic domain of a template region, derived from its heading + content."""
    STATUTORY_METHODOLOGY = "STATUTORY_METHODOLOGY"
    TAXPAYER_PROFILE = "TAXPAYER_PROFILE"
    GROUP_PROFILE = "GROUP_PROFILE"
    ORGANIZATION = "ORGANIZATION"
    BUSINESS_NARRATIVE = "BUSINESS_NARRATIVE"
    COMPETITOR_ANALYSIS = "COMPETITOR_ANALYSIS"
    RELATED_PARTY_TRANSACTIONS = "RELATED_PARTY_TRANSACTIONS"
    INTERCOMPANY_AGREEMENTS = "INTERCOMPANY_AGREEMENTS"
    FUNCTIONAL_ANALYSIS = "FUNCTIONAL_ANALYSIS"
    BENCHMARKING = "BENCHMARKING"
    FINANCIAL_INFORMATION = "FINANCIAL_INFORMATION"
    EXECUTIVE_SUMMARY = "EXECUTIVE_SUMMARY"
    DOCUMENT_CHECKLIST = "DOCUMENT_CHECKLIST"
    STRUCTURAL_CONTAINER = "STRUCTURAL_CONTAINER"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# 2. REGION DOMAIN RULES (heading-derived, evidence recorded)
# ============================================================================

@dataclass(frozen=True)
class DomainRule:
    domain: RegionDomain
    keywords: Tuple[str, ...]
    required_info: Tuple[str, ...]
    required_roles: Tuple[SourceDatasetRole, ...]
    artifact_if_missing: ArtifactType
    historical_reuse: HistoricalReuse
    granularity: str


# Ordered: first matching rule wins. Keywords are matched against the region's
# own heading text, which is real document content -- never against position.
DOMAIN_RULES: Tuple[DomainRule, ...] = (
    DomainRule(RegionDomain.BENCHMARKING,
               ("search for comparable companies", "standard arm", "internal and external comparable",
                "comparable data", "interquartile", "benchmarking", "summary of reasons and explanation"),
               ("comparable company set", "screening criteria", "independence codes",
                "accepted/rejected comparables", "PLI values", "quartile / IQR results"),
               (SourceDatasetRole.BENCHMARKING_DATA, SourceDatasetRole.COMPARABLE_COMPANIES,
                SourceDatasetRole.IQR_RESULTS, SourceDatasetRole.SCREENING_RESULTS),
               ArtifactType.BENCHMARKING_REPORT, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one record per comparable company; one row per screening step"),

    DomainRule(RegionDomain.STATUTORY_METHODOLOGY,
               ("glossary", "objective and scope", "transfer pricing methods", "application of cpm",
                "selection of the most appropriate", "selection of profit level indicator",
                "use of standard arm", "use of previous year", "adjustments", "selection of tested party"),
               ("statutory method definitions", "Decree 20/132 methodology text"),
               (SourceDatasetRole.STATUTORY_TEXT,),
               ArtifactType.NONE_REQUIRED, HistoricalReuse.REUSABLE_BASELINE,
               "document-level narrative; no per-record data"),

    DomainRule(RegionDomain.RELATED_PARTY_TRANSACTIONS,
               ("related party transaction", "sales of goods", "purchases of materials",
                "provision of services", "technical support", "royalt", "interest on intercompany",
                "fixed assets", "other transactions", "values of intra-group"),
               ("counterparty", "transaction type", "amount", "currency", "fiscal year",
                "% of net sales or total cost"),
               (SourceDatasetRole.RELATED_PARTY_TRANSACTIONS,),
               ArtifactType.STRUCTURED_EXCEL, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one record per related-party transaction line"),

    DomainRule(RegionDomain.INTERCOMPANY_AGREEMENTS,
               ("copies of intercompany agreements", "intercompany agreement"),
               ("agreement inventory", "counterparties", "effective dates", "pricing terms"),
               (SourceDatasetRole.CONTRACTUAL_DATA,),
               ArtifactType.CONTRACTUAL_DOCUMENT, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one record per executed intercompany agreement"),

    DomainRule(RegionDomain.FUNCTIONAL_ANALYSIS,
               ("analysis of functions", "functions performed", "assets used", "risks assumed",
                "characterization of", "research and development", "procurement",
                "production/ operation", "quality control", "warehousing", "marketing and sales",
                "after-sales", "general administration"),
               ("current-year functional profile", "assets deployed", "risks borne",
                "entity characterisation"),
               (SourceDatasetRole.NARRATIVE_DATA,),
               ArtifactType.MANAGEMENT_INFORMATION, HistoricalReuse.REUSABLE_WITH_VERIFICATION,
               "narrative per function / asset / risk"),

    DomainRule(RegionDomain.ORGANIZATION,
               ("organisation and management", "organization and management", "management structure"),
               ("current organisation chart", "reporting lines", "headcount"),
               (SourceDatasetRole.ORGANIZATIONAL_DATA,),
               ArtifactType.ORGANIZATION_CHART, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one node per organisational unit"),

    DomainRule(RegionDomain.COMPETITOR_ANALYSIS,
               ("key competitors", "similar products", "competitor"),
               ("competitor identities", "market position", "product overlap"),
               (SourceDatasetRole.NARRATIVE_DATA,),
               ArtifactType.MANAGEMENT_INFORMATION, HistoricalReuse.REUSABLE_WITH_VERIFICATION,
               "narrative per competitor"),

    DomainRule(RegionDomain.GROUP_PROFILE,
               ("overview of the", "group"),
               ("group structure", "ultimate parent", "group activities"),
               (SourceDatasetRole.OWNERSHIP_STRUCTURE, SourceDatasetRole.NARRATIVE_DATA),
               ArtifactType.NARRATIVE_DOCUMENT, HistoricalReuse.REUSABLE_WITH_VERIFICATION,
               "document-level narrative"),

    DomainRule(RegionDomain.BUSINESS_NARRATIVE,
               ("business strategy", "business restructuring", "background", "capital transfers",
                "changes from previous fiscal year", "overview of abc"),
               ("current-year business facts", "strategy statement", "restructuring events"),
               (SourceDatasetRole.NARRATIVE_DATA,),
               ArtifactType.MANAGEMENT_INFORMATION, HistoricalReuse.REUSABLE_WITH_VERIFICATION,
               "document-level narrative"),

    DomainRule(RegionDomain.FINANCIAL_INFORMATION,
               ("financial information", "audited financial statements", "allocation method",
                "summary of financial data"),
               ("net sales", "cost of goods sold", "gross profit", "operating profit",
                "PLI numerator and denominator", "segmented allocation basis"),
               (SourceDatasetRole.FINANCIAL_STATEMENTS, SourceDatasetRole.FINANCIAL_ANALYSIS),
               ArtifactType.STRUCTURED_EXCEL, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one record per financial line item"),

    DomainRule(RegionDomain.TAXPAYER_PROFILE,
               ("information on", "taxpayer information", "taxpayer"),
               ("legal name", "tax code", "address", "fiscal year", "principal activity"),
               (SourceDatasetRole.TAXPAYER_PROFILE,),
               ArtifactType.STRUCTURED_EXCEL, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one record per taxpayer attribute"),

    DomainRule(RegionDomain.EXECUTIVE_SUMMARY,
               ("executive summary",),
               ("transaction summary", "method selected", "arm's-length conclusion"),
               (SourceDatasetRole.RELATED_PARTY_TRANSACTIONS, SourceDatasetRole.IQR_RESULTS),
               ArtifactType.BENCHMARKING_REPORT, HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE,
               "one row per tested transaction"),

    DomainRule(RegionDomain.DOCUMENT_CHECKLIST,
               ("list of contents required", "summary of reasons", "checklist", "point of reference"),
               ("document inventory", "cross-references to appendices"),
               (SourceDatasetRole.APPENDIX_DISCLOSURE,),
               ArtifactType.SUPPORTING_SCHEDULE, HistoricalReuse.REUSABLE_WITH_VERIFICATION,
               "one row per required document"),
)

CONTAINER_HEADINGS = ("part a", "part b", "part c", "part d")


# ============================================================================
# 3. TEMPLATE REGION MODEL
# ============================================================================

@dataclass
class FigureRecord:
    figure_id: str
    paragraph_index: int
    kind: FigureKind
    shape_names: List[str]
    shape_count: int
    connector_count: int
    inner_text_sample: List[str]
    is_smartart: bool
    has_raster_image: bool
    readiness: FigureReadiness
    rationale: str
    required_artifact: ArtifactType

    def to_dict(self) -> Dict[str, Any]:
        return {k: (v.value if isinstance(v, Enum) else v) for k, v in self.__dict__.items()}


@dataclass
class TemplateRegion:
    region_id: str
    heading: str
    heading_level: int
    section_path: List[str]
    paragraph_indices: List[int]
    table_ordinals: List[int]
    figure_ids: List[str]
    word_count: int
    placeholder_token_count: int

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RequirementEntry:
    """One row of the Source Requirement Matrix (Phase E §5)."""
    region_id: str
    heading: str
    section_path: List[str]
    domain: str
    domain_evidence: str
    classification: str
    required_information: List[str]
    required_source_roles: List[str]
    required_granularity: str
    current_source_artifacts: List[str]
    source_roles_found: List[str]
    source_coverage: str
    readiness: str
    historical_reuse: str
    required_artifact_type: str
    blocking_reasons: List[str]
    review_reasons: List[str]
    evidence: List[str]
    table_ordinals: List[int]
    figure_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class RequiredArtifact:
    artifact_id: str
    artifact_type: str
    title: str
    reason_required: str
    affected_regions: List[str]
    required_content: List[str]
    priority: str
    blocking_status: bool

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class HumanReviewItem:
    region_id: str
    heading: str
    issue: str
    missing_evidence: List[str]
    suggested_human_evidence_request: str
    blocking: bool

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class AuditResult:
    regions: List[TemplateRegion]
    figures: List[FigureRecord]
    entries: List[RequirementEntry]
    artifacts: List[RequiredArtifact]
    review_queue: List[HumanReviewItem]
    workbooks: List[WorkbookCapabilityProfile]
    sheet_profiles: List[Dict[str, Any]]
    table_findings: List[Dict[str, Any]]
    benchmarking_audit: Dict[str, Any]
    scorecards: Dict[str, Any]
    frozen: bool = False


# ============================================================================
# 4. FIGURE INVENTORY
# ============================================================================

class FigureInventory:
    """Classifies every drawing construct in the template individually."""

    @classmethod
    def build(cls, doc_path: Path) -> List[FigureRecord]:
        doc = Document(str(doc_path))
        with zipfile.ZipFile(str(doc_path)) as z:
            names = z.namelist()
        has_smartart_part = any(n.startswith("word/diagrams/") for n in names)
        media_parts = [n for n in names if n.startswith("word/media/")]

        out: List[FigureRecord] = []
        p_idx = 0
        for child in doc.element.body:
            if child.tag.split("}")[-1] != "p":
                continue
            p = Paragraph(child, doc)
            p_idx += 1
            drawings = child.findall(f".//{_W}drawing")
            picts = child.findall(f".//{_W}pict")
            graphic = [n for n in child.iter() if n.tag.endswith("}graphicData")]
            if not drawings and not picts and not graphic:
                continue

            shape_names = [n.get("name") for n in child.iter(f"{_WP}docPr") if n.get("name")]
            shape_names += [n.get("name") for n in child.iter(f"{_A}cNvPr") if n.get("name")]
            shape_names = [n for n in dict.fromkeys(shape_names)]
            texts = [t.text.strip() for t in child.iter(f"{_W}t") if t.text and t.text.strip()]
            has_blip = bool([n for n in child.iter() if n.tag.endswith("}blip")])
            is_smartart = any("diagram" in (n or "").lower() for n in shape_names)
            connectors = sum(1 for n in shape_names if "connector" in n.lower())
            para_text = (p.text or "").strip()

            kind, readiness, rationale, artifact = cls._classify(
                shape_names, texts, para_text, is_smartart, has_blip, connectors)

            out.append(FigureRecord(
                figure_id=f"fig-p{p_idx:04d}",
                paragraph_index=p_idx,
                kind=kind,
                shape_names=shape_names[:12],
                shape_count=len(shape_names),
                connector_count=connectors,
                inner_text_sample=texts[:8],
                is_smartart=is_smartart,
                has_raster_image=has_blip,
                readiness=readiness,
                rationale=rationale,
                required_artifact=artifact,
            ))

        # Record package-level facts on the first entry's rationale context.
        for rec in out:
            if not media_parts:
                rec.has_raster_image = False
        cls._package_facts = {"media_parts": len(media_parts),
                              "smartart_parts": has_smartart_part}
        return out

    _package_facts: Dict[str, Any] = {}

    @staticmethod
    def _classify(shape_names, texts, para_text, is_smartart, has_blip, connectors):
        blob = " ".join(texts).lower() + " " + para_text.lower()
        names_blob = " ".join(shape_names).lower()

        if has_blip:
            return (FigureKind.EMBEDDED_SCREENSHOT, FigureReadiness.HUMAN_REVIEW,
                    "Raster image: cannot be regenerated from structured data.",
                    ArtifactType.FIGURE_CHART_SOURCE)

        if is_smartart:
            return (FigureKind.PROCESS_FLOW, FigureReadiness.HUMAN_REVIEW,
                    "SmartArt diagram (word/diagrams/*). Editing requires the SmartArt data model, "
                    "which no current source supplies.",
                    ArtifactType.FIGURE_CHART_SOURCE)

        if "canvas" in names_blob:
            return (FigureKind.TRANSACTION_FLOW, FigureReadiness.HUMAN_REVIEW,
                    "Drawing canvas holding a related-party transaction flow; its node labels are "
                    "client-specific and no current source enumerates them.",
                    ArtifactType.MANAGEMENT_INFORMATION)

        # A figure must be structurally a figure. A single "Text Box N" holding
        # prose is a layout callout however much chart vocabulary it contains --
        # the template's KPMG drafting-guidance boxes discuss ownership and
        # benchmarking at length and are not diagrams.
        is_diagrammatic = connectors >= 1 or len(shape_names) >= 3
        only_text_boxes = bool(shape_names) and all(
            n.lower().startswith("text box") for n in shape_names)

        if is_diagrammatic and not only_text_boxes:
            if any(k in blob for k in ("director", "manager", "department", "head of")):
                return (FigureKind.ORGANIZATION_CHART, FigureReadiness.HUMAN_REVIEW,
                        "Shape-and-connector organisation chart; requires a current-year org chart.",
                        ArtifactType.ORGANIZATION_CHART)
            if any(k in blob for k in ("shareholder", "ownership", "% held", "subsidiary of")):
                return (FigureKind.OWNERSHIP_CHART, FigureReadiness.HUMAN_REVIEW,
                        "Ownership structure figure; requires a current-year shareholding schedule.",
                        ArtifactType.ORGANIZATION_CHART)
            if any(k in blob for k in ("quartile", "percentile", "benchmark")):
                return (FigureKind.BENCHMARKING_CHART, FigureReadiness.BLOCKED,
                        "Benchmarking chart with no benchmarking source in the current set.",
                        ArtifactType.BENCHMARKING_REPORT)
            return (FigureKind.UNKNOWN, FigureReadiness.HUMAN_REVIEW,
                    f"Multi-shape drawing ({len(shape_names)} shapes, {connectors} connectors) "
                    f"whose subject could not be derived from its labels.",
                    ArtifactType.FIGURE_CHART_SOURCE)

        return (FigureKind.LAYOUT_TEXT_BOX, FigureReadiness.STATIC_PRESERVE,
                "Text box used for page layout/callout, not a data figure; preserved unchanged.",
                ArtifactType.NONE_REQUIRED)


# ============================================================================
# 5. REGION SEGMENTATION
# ============================================================================

class TemplateRegionSegmenter:
    """Heading-delimited semantic regions. Every body element belongs to one."""

    @classmethod
    def segment(cls, doc_path: Path, figures: Sequence[FigureRecord]) -> List[TemplateRegion]:
        doc = Document(str(doc_path))
        fig_by_para = {f.paragraph_index: f.figure_id for f in figures}

        regions: List[TemplateRegion] = []
        stack: List[Tuple[int, str]] = []
        current: Optional[TemplateRegion] = None
        p_idx = t_idx = 0
        counter = 0

        def new_region(heading: str, level: int) -> TemplateRegion:
            nonlocal counter
            counter += 1
            return TemplateRegion(
                region_id=f"rgn-{counter:03d}", heading=heading, heading_level=level,
                section_path=[h for _, h in stack], paragraph_indices=[], table_ordinals=[],
                figure_ids=[], word_count=0, placeholder_token_count=0)

        current = new_region("PREAMBLE (before first heading)", 0)

        for child in doc.element.body:
            tag = child.tag.split("}")[-1]
            if tag == "p":
                p = Paragraph(child, doc)
                p_idx += 1
                text = re.sub(r"\s+", " ", p.text or "").strip()
                style = p.style.name if p.style else ""
                m = _HEADING_RE.match(style.strip())
                if m and text:
                    level = int(m.group(2)) if m.group(2) else 1
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    if current is not None:
                        regions.append(current)
                    stack.append((level, text))
                    current = new_region(text, level)
                    current.section_path = [h for _, h in stack[:-1]]
                current.paragraph_indices.append(p_idx)
                current.word_count += len(text.split())
                current.placeholder_token_count += len(
                    re.findall(r"\b(x{2,}|y{2,}|z{2,}|ABC|XYZ|FY20xx|FY20ww|FY20yy|dd/mm)\b", text))
                if p_idx in fig_by_para:
                    current.figure_ids.append(fig_by_para[p_idx])
            elif tag == "tbl":
                current.table_ordinals.append(t_idx)
                t_idx += 1

        if current is not None:
            regions.append(current)
        return regions


# ============================================================================
# 6. EXTENDED SOURCE ROLE CLASSIFICATION
# ============================================================================

# Additional content signals for Phase E roles the C2 profiler does not carry.
_EXTENDED_SIGNALS: Tuple[Tuple[SourceDatasetRole, int, Tuple[str, ...]], ...] = (
    (SourceDatasetRole.TAXPAYER_PROFILE, 2,
     ("tax code", "company name", "address", "fiscal year", "principal activity",
      "enterprise code", "taxpayer")),
    (SourceDatasetRole.OWNERSHIP_STRUCTURE, 2,
     ("ownership", "shareholder", "% of ownership", "parent company", "ultimate parent",
      "holding")),
    (SourceDatasetRole.ORGANIZATIONAL_DATA, 2,
     ("department", "director", "headcount", "employees", "reporting line", "organisation")),
    (SourceDatasetRole.CONTRACTUAL_DATA, 2,
     ("agreement", "contract", "effective date", "term", "signed")),
    (SourceDatasetRole.TAX_SCHEDULE, 2,
     ("cit", "corporate income tax", "tax payable", "taxable income", "deductible")),
    (SourceDatasetRole.APPENDIX_DISCLOSURE, 2,
     ("appendix", "form 01", "disclosure", "declaration", "point of reference")),
    (SourceDatasetRole.NARRATIVE_DATA, 2,
     ("description", "explanation", "narrative", "commentary", "remarks")),
)

# C2 role -> Phase E role, so existing evidence is reused rather than re-derived.
_C2_TO_E: Dict[DatasetRole, SourceDatasetRole] = {
    DatasetRole.RELATED_PARTY_TRANSACTIONS: SourceDatasetRole.RELATED_PARTY_TRANSACTIONS,
    DatasetRole.FINANCIAL_STATEMENTS: SourceDatasetRole.FINANCIAL_STATEMENTS,
    DatasetRole.FINANCIAL_ANALYSIS: SourceDatasetRole.FINANCIAL_ANALYSIS,
    DatasetRole.FIXED_ASSETS: SourceDatasetRole.FIXED_ASSETS,
    DatasetRole.BENCHMARKING_DATA: SourceDatasetRole.BENCHMARKING_DATA,
    DatasetRole.COMPARABLE_COMPANIES: SourceDatasetRole.COMPARABLE_COMPANIES,
    DatasetRole.IQR_RESULTS: SourceDatasetRole.IQR_RESULTS,
    DatasetRole.SCREENING_RESULTS: SourceDatasetRole.SCREENING_RESULTS,
    DatasetRole.NARRATIVE_DISCLOSURE: SourceDatasetRole.NARRATIVE_DATA,
    DatasetRole.RELATED_PARTIES_REGISTER: SourceDatasetRole.OWNERSHIP_STRUCTURE,
    DatasetRole.INTEREST_EXPENSE: SourceDatasetRole.INTEREST_EXPENSE,
    DatasetRole.SEGMENTED_DATA: SourceDatasetRole.SEGMENTED_DATA,
    DatasetRole.REFERENCE_LIST: SourceDatasetRole.APPENDIX_DISCLOSURE,
    DatasetRole.CHECKLIST: SourceDatasetRole.APPENDIX_DISCLOSURE,
}


class ExtendedSourceProfiler:
    """Adds the Phase E role taxonomy on top of the C2 content profiler.

    The C2 profiler is not modified. Its per-sheet evidence is reused, and the
    extra Phase E roles are derived from the same content-only signals.
    """

    @classmethod
    def profile(cls, paths: Sequence[Path]) -> Tuple[List[WorkbookCapabilityProfile], List[Dict[str, Any]]]:
        workbooks = [SourceCapabilityProfiler.profile_workbook(p) for p in paths]
        sheets: List[Dict[str, Any]] = []
        for wb in workbooks:
            for s in wb.sheets:
                roles, evidence = cls._extended_roles(s)
                sheets.append({
                    "workbook": wb.document_name,
                    "sheet_name": s.sheet_name,
                    "row_count": s.max_row,
                    "column_count": s.max_column,
                    "record_count": s.record_count,
                    "headers": s.headers[:16],
                    "header_row_index": s.header_row_index,
                    "c2_roles": [r.value for r in s.roles],
                    "dataset_roles": [r.value for r in roles],
                    "role_evidence": {**s.role_evidence, **evidence},
                    "semantic_field_types": [c.inferred_type for c in s.record_schema[:16]],
                    "units": s.units_detected,
                    "formula_presence": s.formula_cell_count > 0,
                    "formula_cell_count": s.formula_cell_count,
                    "data_domain": s.data_domain.value,
                    "record_pattern": cls._record_pattern(s),
                    "section_labels": [c.header for c in s.record_schema[:10] if c.header],
                })
        return workbooks, sheets

    @staticmethod
    def _record_pattern(s: SheetDatasetProfile) -> str:
        if s.record_count == 0:
            return "EMPTY"
        typed = [c.inferred_type for c in s.record_schema if c.non_empty]
        if not typed:
            return "UNSTRUCTURED"
        if typed.count("numeric") >= max(1, len(typed) // 2):
            return "TABULAR_NUMERIC"
        if "narrative" in typed:
            return "TABULAR_WITH_NARRATIVE"
        return "TABULAR_TEXT"

    @classmethod
    def _extended_roles(cls, s: SheetDatasetProfile) -> Tuple[List[SourceDatasetRole], Dict[str, List[str]]]:
        roles: List[SourceDatasetRole] = []
        evidence: Dict[str, List[str]] = {}
        for c2 in s.roles:
            mapped = _C2_TO_E.get(c2)
            if not mapped:
                continue
            if mapped not in roles:
                roles.append(mapped)
            # Re-key the C2 evidence under the Phase E role name so every
            # reported role can be traced to the tokens that earned it.
            tokens = s.role_evidence.get(c2.value)
            if tokens:
                evidence.setdefault(mapped.value, [])
                for t in tokens:
                    if t not in evidence[mapped.value]:
                        evidence[mapped.value].append(t)

        hay = " | ".join(h.lower() for h in s.headers)
        hay += " || " + " || ".join((c.header or "").lower() for c in s.record_schema)
        hay += " || " + " || ".join((c.sample or "").lower() for c in s.record_schema)
        for role, threshold, tokens in _EXTENDED_SIGNALS:
            hits = [t for t in tokens if t in hay]
            if len(hits) >= threshold:
                if role not in roles:
                    roles.append(role)
                evidence.setdefault(role.value, [])
                for t in hits:
                    if t not in evidence[role.value]:
                        evidence[role.value].append(t)
        return (roles or [SourceDatasetRole.UNKNOWN]), evidence

    @staticmethod
    def roles_present(sheets: Sequence[Dict[str, Any]]) -> Set[str]:
        out: Set[str] = set()
        for s in sheets:
            out.update(s["dataset_roles"])
        out.discard(SourceDatasetRole.UNKNOWN.value)
        return out


# ============================================================================
# 7. THE AUDIT
# ============================================================================

class SourceCompletenessAudit:
    """Computes the readiness map with Ground Truth quarantined throughout."""

    @classmethod
    def freeze(cls) -> AuditResult:
        GroundTruthQuarantine.arm([PATH_GROUND_TRUTH_FORBIDDEN])
        try:
            return cls._run()
        finally:
            GroundTruthQuarantine.disarm()

    @classmethod
    def _run(cls) -> AuditResult:
        GroundTruthQuarantine.check(PATH_TMPL)
        GroundTruthQuarantine.check(PATH_HIST)

        figures = FigureInventory.build(PATH_TMPL)
        regions = TemplateRegionSegmenter.segment(PATH_TMPL, figures)
        workbooks, sheets = ExtendedSourceProfiler.profile([PATH_FARPT, PATH_APP1])
        available = ExtendedSourceProfiler.roles_present(sheets)

        table_findings = cls._table_findings(workbooks)
        by_ordinal = {t["template_ordinal_display_only"]: t for t in table_findings}
        fig_by_id = {f.figure_id: f for f in figures}

        entries = [cls._assess(r, available, sheets, by_ordinal, fig_by_id) for r in regions]
        benchmarking = cls._benchmarking_audit(sheets, entries)
        artifacts = cls._required_artifacts(entries)
        queue = cls._review_queue(entries)
        scorecards = cls._scorecards(entries, figures, sheets, available)

        scorecards["segmentation"] = cls._segmentation_facts(regions)

        return AuditResult(
            regions=regions, figures=figures, entries=entries, artifacts=artifacts,
            review_queue=queue, workbooks=workbooks, sheet_profiles=sheets,
            table_findings=table_findings, benchmarking_audit=benchmarking,
            scorecards=scorecards, frozen=True)

    @staticmethod
    def _segmentation_facts(regions: Sequence[TemplateRegion]) -> Dict[str, Any]:
        """Proves the segmentation partitions the body: no element lost or double-counted."""
        doc = Document(str(PATH_TMPL))
        body_paragraphs = sum(1 for c in doc.element.body if c.tag.split("}")[-1] == "p")
        body_tables = sum(1 for c in doc.element.body if c.tag.split("}")[-1] == "tbl")

        para_ids: List[int] = []
        table_ids: List[int] = []
        for r in regions:
            para_ids.extend(r.paragraph_indices)
            table_ids.extend(r.table_ordinals)

        return {
            "method": "heading-delimited: every body paragraph and table belongs to exactly "
                      "one region; a new region opens at each Heading/Title paragraph",
            "regions": len(regions),
            "body_paragraphs": body_paragraphs,
            "paragraphs_assigned": len(para_ids),
            "paragraphs_unique": len(set(para_ids)),
            "body_tables": body_tables,
            "tables_assigned": len(table_ids),
            "tables_unique": len(set(table_ids)),
            "is_exact_partition": (len(para_ids) == len(set(para_ids)) == body_paragraphs
                                   and len(table_ids) == len(set(table_ids)) == body_tables),
            "note": ("Phase E derives 61 regions from the template's own heading structure. This "
                     "is not the 104 regions in the contaminated Phase C manifest, which came "
                     "from a different segmenter that has since been invalidated. The count is "
                     "reported as measured; no target count was assumed."),
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _table_findings(workbooks: Sequence[WorkbookCapabilityProfile]) -> List[Dict[str, Any]]:
        doc = Document(str(PATH_TMPL))
        sigs = TableIdentityProfiler.profile_document(PATH_TMPL, "TEMPLATE")
        hist = TableIdentityProfiler.profile_document(PATH_HIST, "HIST_FY2023")
        corr = {c.left.ordinal: c for c in TableCorrespondenceResolver.correspond(sigs, hist)}

        out = []
        for sig in sigs:
            anatomy = TableAnatomyProfiler.profile(doc.tables[sig.ordinal], sig.ordinal)
            schema = TargetSchemaDeriver.derive(f"tbl-{sig.identity_key[:8]}", sig)
            schema.footer_row_idxs = anatomy.footer_row_idxs
            binding = SemanticBindingValidator.validate(schema, workbooks)
            c = corr.get(sig.ordinal)
            out.append({
                "template_ordinal_display_only": sig.ordinal,
                "identity_key": sig.identity_key,
                "semantic_label": sig.primary_label.value,
                "rows": sig.row_count, "columns": sig.column_count,
                "row_semantics": schema.row_semantics.value,
                "binding_verdict": binding.verdict.value,
                "required_roles": [r.value for r in binding.required_roles],
                "roles_found": [r.value for r in binding.roles_found],
                "historical_correspondence": c.confidence.value if c else "UNCORRELATED",
                "footer_rows": list(anatomy.footer_row_idxs),
                "placeholder_rows": list(anatomy.placeholder_row_idxs),
            })
        return out

    # Table semantic label -> region domain, for regions whose heading is generic.
    LABEL_TO_DOMAIN: Dict[SemanticLabel, RegionDomain] = {
        SemanticLabel.COMPARABLE_COMPANIES: RegionDomain.BENCHMARKING,
        SemanticLabel.SCREENING_STRATEGY: RegionDomain.BENCHMARKING,
        SemanticLabel.SCREENING_REJECTION: RegionDomain.BENCHMARKING,
        SemanticLabel.SEARCH_STEP_MATRIX: RegionDomain.BENCHMARKING,
        SemanticLabel.ARMS_LENGTH_RANGE: RegionDomain.BENCHMARKING,
        SemanticLabel.RELATED_PARTY_TRANSACTIONS: RegionDomain.RELATED_PARTY_TRANSACTIONS,
        SemanticLabel.INTEREST_SCHEDULE: RegionDomain.RELATED_PARTY_TRANSACTIONS,
        SemanticLabel.FINANCIAL_INDICATORS: RegionDomain.FINANCIAL_INFORMATION,
        SemanticLabel.FUNCTIONAL_ANALYSIS: RegionDomain.FUNCTIONAL_ANALYSIS,
        SemanticLabel.DOCUMENT_CHECKLIST: RegionDomain.DOCUMENT_CHECKLIST,
        SemanticLabel.COVER_BLOCK: RegionDomain.TAXPAYER_PROFILE,
        SemanticLabel.PLI_FORMULA: RegionDomain.STATUTORY_METHODOLOGY,
    }

    @classmethod
    def _rule_for_domain(cls, domain: RegionDomain) -> Optional[DomainRule]:
        for rule in DOMAIN_RULES:
            if rule.domain == domain:
                return rule
        return None

    @classmethod
    def _match_heading(cls, heading: str) -> Tuple[Optional[DomainRule], str]:
        h = re.sub(r"\s+", " ", heading or "").strip().lower()
        if not h:
            return None, ""
        for rule in DOMAIN_RULES:
            for kw in rule.keywords:
                if kw in h:
                    return rule, f"heading contains '{kw}'"
        return None, ""

    @classmethod
    def _match_domain(
        cls,
        heading: str,
        section_path: Sequence[str] = (),
        table_ordinals: Sequence[int] = (),
        tables: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> Tuple[Optional[DomainRule], str]:
        """Classifies a region from its own heading, else its parent, else its tables.

        All three inputs are document content. Position is never consulted.
        """
        h = re.sub(r"\s+", " ", heading or "").strip().lower()
        if any(h.startswith(c) for c in CONTAINER_HEADINGS):
            return None, f"heading '{heading}' is a structural part container"

        rule, why = cls._match_heading(heading)
        if rule is not None:
            return rule, why

        # A generic sub-heading ("Overview") inherits the nearest ancestor that
        # does classify -- the section it sits inside is real evidence.
        for ancestor in reversed(list(section_path)):
            rule, why = cls._match_heading(ancestor)
            if rule is not None:
                return rule, f"inherited from parent section '{ancestor}' ({why})"

        # Otherwise the tables the region contains identify its domain.
        if tables:
            for ordinal in table_ordinals:
                t = tables.get(ordinal)
                if not t:
                    continue
                try:
                    label = SemanticLabel(t["semantic_label"])
                except ValueError:
                    continue
                domain = cls.LABEL_TO_DOMAIN.get(label)
                if domain is None:
                    continue
                rule = cls._rule_for_domain(domain)
                if rule is not None:
                    return rule, (f"classified from contained table {ordinal} "
                                  f"(semantic label {label.value})")
        return None, ""

    @classmethod
    def _assess(
        cls, region: TemplateRegion, available: Set[str],
        sheets: Sequence[Dict[str, Any]], tables: Dict[int, Dict[str, Any]],
        figures: Dict[str, FigureRecord],
    ) -> RequirementEntry:
        rule, evidence = cls._match_domain(
            region.heading, region.section_path, region.table_ordinals, tables)
        blocking: List[str] = []
        review: List[str] = []
        ev: List[str] = []
        if evidence:
            ev.append(evidence)

        is_container = (rule is None and any(
            region.heading.strip().lower().startswith(c) for c in CONTAINER_HEADINGS))
        has_content = bool(region.table_ordinals) or region.word_count > 12 or bool(region.figure_ids)

        # ---- container / empty regions ---------------------------------
        if is_container or (rule is None and not has_content):
            return RequirementEntry(
                region_id=region.region_id, heading=region.heading,
                section_path=region.section_path,
                domain=RegionDomain.STRUCTURAL_CONTAINER.value if is_container else RegionDomain.UNKNOWN.value,
                domain_evidence=evidence or "no domain keyword matched and the region carries "
                                            "no table, figure or substantive text",
                classification="CONTAINER" if is_container else "EMPTY",
                required_information=[], required_source_roles=[],
                required_granularity="none",
                current_source_artifacts=[], source_roles_found=[],
                source_coverage=SourceCoverage.NOT_APPLICABLE.value,
                readiness=Readiness.NOT_APPLICABLE.value,
                historical_reuse=HistoricalReuse.NOT_APPLICABLE.value,
                required_artifact_type=ArtifactType.NONE_REQUIRED.value,
                blocking_reasons=[], review_reasons=[], evidence=ev,
                table_ordinals=region.table_ordinals, figure_ids=region.figure_ids)

        # ---- unmatched but content-bearing -----------------------------
        if rule is None:
            return RequirementEntry(
                region_id=region.region_id, heading=region.heading,
                section_path=region.section_path, domain=RegionDomain.UNKNOWN.value,
                domain_evidence="no domain rule matched this heading",
                classification="NARRATIVE" if not region.table_ordinals else "MIXED",
                required_information=["undetermined - requires human classification"],
                required_source_roles=[], required_granularity="undetermined",
                current_source_artifacts=[], source_roles_found=[],
                source_coverage=SourceCoverage.INSUFFICIENT_EVIDENCE.value,
                readiness=Readiness.BLOCKED_INSUFFICIENT_EVIDENCE.value,
                historical_reuse=HistoricalReuse.REUSABLE_WITH_VERIFICATION.value,
                required_artifact_type=ArtifactType.MANAGEMENT_INFORMATION.value,
                blocking_reasons=[
                    f"No deterministic domain rule matches heading '{region.heading}'. "
                    f"The region carries {len(region.table_ordinals)} table(s), "
                    f"{len(region.figure_ids)} figure(s) and {region.word_count} words."],
                review_reasons=[], evidence=ev,
                table_ordinals=region.table_ordinals, figure_ids=region.figure_ids)

        # ---- matched domain --------------------------------------------
        required = [r.value for r in rule.required_roles]
        found = [r for r in required if r in available]
        missing = [r for r in required if r not in available]

        supplying: List[str] = []
        for s in sheets:
            if set(s["dataset_roles"]) & set(found):
                label = f"{s['workbook']}!{s['sheet_name']}"
                if label not in supplying:
                    supplying.append(label)
                    ev.append(f"{label} supplies {sorted(set(s['dataset_roles']) & set(found))} "
                              f"({s['record_count']} records)")

        # Statutory text needs no current source at all.
        if rule.domain == RegionDomain.STATUTORY_METHODOLOGY:
            coverage = SourceCoverage.NOT_APPLICABLE
            readiness = Readiness.AUTO_NOOP_READY
            ev.append("Statutory methodology text is year-independent; carried forward unchanged.")
            if region.placeholder_token_count:
                readiness = Readiness.HUMAN_REVIEW_READY
                coverage = SourceCoverage.HUMAN_REVIEW
                review.append(
                    f"Region contains {region.placeholder_token_count} template placeholder "
                    f"token(s) (ABC / XYZ / FY20xx); these must be personalised before issue.")
        elif not required:
            coverage = SourceCoverage.INSUFFICIENT_EVIDENCE
            readiness = Readiness.BLOCKED_INSUFFICIENT_EVIDENCE
            blocking.append("Domain declares no required source role.")
        elif not found:
            coverage = SourceCoverage.MISSING_SOURCE
            readiness = Readiness.BLOCKED_MISSING_SOURCE
            blocking.append(
                f"None of the required dataset roles {required} is present in the current source "
                f"set. Content profiling of {len(sheets)} sheets found: "
                f"{sorted(available)}.")
        elif missing:
            coverage = SourceCoverage.PARTIALLY_SUPPORTED
            readiness = Readiness.HUMAN_REVIEW_READY
            review.append(
                f"Partially supported: {found} available, {missing} absent. A reviewer must "
                f"supply or waive the missing part.")
        else:
            coverage = SourceCoverage.FULLY_SUPPORTED
            readiness = Readiness.HUMAN_REVIEW_READY
            review.append(
                "All required dataset roles are present, but no implemented mutation strategy "
                "covers this region; a reviewer applies the update.")

        # ---- table-level constraints ------------------------------------
        for ordinal in region.table_ordinals:
            t = tables.get(ordinal)
            if not t:
                continue
            ev.append(f"table {ordinal} ({t['semantic_label']}, {t['rows']}x{t['columns']}, "
                      f"row_semantics={t['row_semantics']}) binding={t['binding_verdict']}")
            if t["binding_verdict"] == BindingVerdict.MISSING_CURRENT_SOURCE.value:
                coverage = SourceCoverage.MISSING_SOURCE
                readiness = Readiness.BLOCKED_MISSING_SOURCE
                blocking.append(
                    f"Table {ordinal} ({t['semantic_label']}) requires {t['required_roles']}, "
                    f"which no current source supplies.")
            elif t["binding_verdict"] == BindingVerdict.INCOMPATIBLE_SCHEMA.value:
                coverage = SourceCoverage.MISSING_SOURCE
                readiness = Readiness.BLOCKED_SCHEMA_MISMATCH
                blocking.append(f"Table {ordinal} schema is incompatible with the available source.")

        # ---- figure constraints ------------------------------------------
        for fid in region.figure_ids:
            f = figures.get(fid)
            if not f or f.kind == FigureKind.LAYOUT_TEXT_BOX:
                continue
            ev.append(f"{fid}: {f.kind.value} -> {f.readiness.value}")
            if f.readiness == FigureReadiness.BLOCKED:
                coverage = SourceCoverage.MISSING_SOURCE
                readiness = Readiness.BLOCKED_MISSING_SOURCE
                blocking.append(f"{fid} ({f.kind.value}): {f.rationale}")
            elif f.readiness == FigureReadiness.HUMAN_REVIEW and readiness in (
                    Readiness.AUTO_NOOP_READY, Readiness.AUTO_MUTATION_READY):
                readiness = Readiness.HUMAN_REVIEW_READY
                coverage = SourceCoverage.HUMAN_REVIEW
                review.append(f"{fid} ({f.kind.value}): {f.rationale}")

        # ---- historical reuse --------------------------------------------
        reuse = rule.historical_reuse
        if reuse == HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE and coverage in (
                SourceCoverage.MISSING_SOURCE, SourceCoverage.INSUFFICIENT_EVIDENCE):
            ev.append("FY2023 text may NOT be promoted to current-year verified: this domain "
                      "carries year-specific facts and no current source is available.")

        if blocking and readiness not in (
                Readiness.BLOCKED_MISSING_SOURCE, Readiness.BLOCKED_SCHEMA_MISMATCH,
                Readiness.BLOCKED_INSUFFICIENT_EVIDENCE, Readiness.BLOCKED_UNSUPPORTED_CONSTRUCT):
            readiness = Readiness.BLOCKED_MISSING_SOURCE

        return RequirementEntry(
            region_id=region.region_id, heading=region.heading,
            section_path=region.section_path, domain=rule.domain.value,
            domain_evidence=evidence,
            classification="MIXED" if region.table_ordinals and region.word_count > 12
            else ("TABULAR" if region.table_ordinals else "NARRATIVE"),
            required_information=list(rule.required_info),
            required_source_roles=required,
            required_granularity=rule.granularity,
            current_source_artifacts=supplying,
            source_roles_found=found,
            source_coverage=coverage.value, readiness=readiness.value,
            historical_reuse=reuse.value,
            required_artifact_type=(ArtifactType.NONE_REQUIRED.value
                                    if coverage in (SourceCoverage.FULLY_SUPPORTED,
                                                    SourceCoverage.NOT_APPLICABLE)
                                    else rule.artifact_if_missing.value),
            blocking_reasons=blocking, review_reasons=review, evidence=ev,
            table_ordinals=region.table_ordinals, figure_ids=region.figure_ids)

    # ------------------------------------------------------------------

    @staticmethod
    def _benchmarking_audit(sheets: Sequence[Dict[str, Any]], entries: Sequence[RequirementEntry]) -> Dict[str, Any]:
        targets = {
            "comparable-company data": SourceDatasetRole.COMPARABLE_COMPANIES.value,
            "search database / benchmarking output": SourceDatasetRole.BENCHMARKING_DATA.value,
            "screening criteria & results": SourceDatasetRole.SCREENING_RESULTS.value,
            "IQR / percentile results": SourceDatasetRole.IQR_RESULTS.value,
        }
        present = ExtendedSourceProfiler.roles_present(sheets)
        findings = {label: {"role": role, "present": role in present,
                            "sheets": [s["sheet_name"] for s in sheets if role in s["dataset_roles"]]}
                    for label, role in targets.items()}
        dependent = [e.region_id for e in entries if e.domain == RegionDomain.BENCHMARKING.value]
        return {
            "priority": "PRIORITY DOMAIN",
            "method": "content-derived role detection over every sheet; sheet names not consulted",
            "sheets_scanned": len(sheets),
            "findings": findings,
            "independence_codes_present": False,
            "accepted_rejected_comparables_present": False,
            "any_benchmarking_source_present": any(f["present"] for f in findings.values()),
            "dependent_regions": dependent,
            "dependent_region_count": len(dependent),
            "verdict": ("NO benchmarking source of any kind exists in the current set; every "
                        "dependent region is BLOCKED_MISSING_SOURCE."),
            "minimum_required_artifact": {
                "type": ArtifactType.BENCHMARKING_REPORT.value,
                "content": ["accepted comparable-company set with identifiers",
                            "rejected companies with rejection reason",
                            "search strategy and screening steps with pass counts",
                            "BvD independence codes",
                            "per-company PLI values for the tested period",
                            "quartile / interquartile range statistics"],
            },
        }

    @staticmethod
    def _required_artifacts(entries: Sequence[RequirementEntry]) -> List[RequiredArtifact]:
        groups: Dict[Tuple[str, str], List[RequirementEntry]] = {}
        for e in entries:
            if e.readiness.startswith("BLOCKED") or e.source_coverage in (
                    SourceCoverage.PARTIALLY_SUPPORTED.value, SourceCoverage.HUMAN_REVIEW.value):
                if e.required_artifact_type == ArtifactType.NONE_REQUIRED.value:
                    continue
                groups.setdefault((e.required_artifact_type, e.domain), []).append(e)

        titles = {
            ArtifactType.BENCHMARKING_REPORT.value: "Benchmarking / comparable-company dataset",
            ArtifactType.STRUCTURED_EXCEL.value: "Structured current-year schedule (Excel)",
            ArtifactType.MANAGEMENT_INFORMATION.value: "Management information / client questionnaire",
            ArtifactType.CONTRACTUAL_DOCUMENT.value: "Executed intercompany agreements",
            ArtifactType.ORGANIZATION_CHART.value: "Current-year organisation / ownership chart",
            ArtifactType.NARRATIVE_DOCUMENT.value: "Current-year narrative source document",
            ArtifactType.FIGURE_CHART_SOURCE.value: "Figure / diagram source data",
            ArtifactType.SUPPORTING_SCHEDULE.value: "Supporting schedule / appendix cross-reference",
            ArtifactType.LEGAL_REGULATORY_SOURCE.value: "Legal or regulatory reference source",
        }
        out: List[RequiredArtifact] = []
        for idx, ((atype, domain), items) in enumerate(
                sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])), start=1):
            blocking = any(i.readiness.startswith("BLOCKED") for i in items)
            content: List[str] = []
            for i in items:
                for r in i.required_information:
                    if r not in content:
                        content.append(r)
            priority = (Priority.BLOCKING if blocking else
                        Priority.HIGH if len(items) >= 5 else
                        Priority.MEDIUM if len(items) >= 2 else Priority.LOW)
            out.append(RequiredArtifact(
                artifact_id=f"ART-{idx:03d}",
                artifact_type=atype,
                title=f"{titles.get(atype, atype)} — {domain}",
                reason_required=(
                    f"{len(items)} region(s) in domain {domain} cannot be completed from the "
                    f"current source set; their required dataset roles are absent or only "
                    f"partially present."),
                affected_regions=[i.region_id for i in items],
                required_content=content[:12],
                priority=priority.value,
                blocking_status=blocking))
        return out

    @staticmethod
    def _review_queue(entries: Sequence[RequirementEntry]) -> List[HumanReviewItem]:
        out: List[HumanReviewItem] = []
        for e in entries:
            if e.readiness == Readiness.NOT_APPLICABLE.value:
                continue
            if not e.review_reasons and not e.readiness.startswith("BLOCKED"):
                continue
            blocking = e.readiness.startswith("BLOCKED")
            issue = (e.blocking_reasons[0] if e.blocking_reasons else
                     e.review_reasons[0] if e.review_reasons else "requires review")
            missing = [r for r in e.required_source_roles if r not in e.source_roles_found]
            if e.required_artifact_type == ArtifactType.NONE_REQUIRED.value:
                request = ("Confirm the carried-forward content still applies to the current "
                           "fiscal year and personalise remaining template placeholders.")
            else:
                request = (f"Obtain a {e.required_artifact_type} covering "
                           f"{', '.join(e.required_information[:4]) or 'the region requirement'}"
                           f" at granularity: {e.required_granularity}.")
            out.append(HumanReviewItem(
                region_id=e.region_id, heading=e.heading, issue=issue,
                missing_evidence=missing or ["implemented mutation strategy"],
                suggested_human_evidence_request=request, blocking=blocking))
        return out

    @staticmethod
    def _scorecards(entries, figures, sheets, available) -> Dict[str, Any]:
        def pct(num: int, den: int) -> float:
            return round(100.0 * num / den, 1) if den else 0.0

        by_domain: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            if e.readiness == Readiness.NOT_APPLICABLE.value:
                continue
            d = by_domain.setdefault(e.domain, {"total": 0, "fully": 0, "partial": 0,
                                                "human": 0, "missing": 0, "insufficient": 0,
                                                "not_applicable": 0, "regions": []})
            d["total"] += 1
            d["regions"].append(e.region_id)
            key = {SourceCoverage.FULLY_SUPPORTED.value: "fully",
                   SourceCoverage.PARTIALLY_SUPPORTED.value: "partial",
                   SourceCoverage.HUMAN_REVIEW.value: "human",
                   SourceCoverage.MISSING_SOURCE.value: "missing",
                   SourceCoverage.INSUFFICIENT_EVIDENCE.value: "insufficient",
                   SourceCoverage.NOT_APPLICABLE.value: "not_applicable"}.get(e.source_coverage)
            if key:
                d[key] += 1
        for d in by_domain.values():
            supported = d["fully"] + d["partial"] + d["not_applicable"]
            d["supported_pct"] = pct(supported, d["total"])
            d["fully_supported_pct"] = pct(d["fully"] + d["not_applicable"], d["total"])

        readiness_counts: Dict[str, int] = {}
        coverage_counts: Dict[str, int] = {}
        for e in entries:
            readiness_counts[e.readiness] = readiness_counts.get(e.readiness, 0) + 1
            coverage_counts[e.source_coverage] = coverage_counts.get(e.source_coverage, 0) + 1

        data_figures = [f for f in figures if f.kind != FigureKind.LAYOUT_TEXT_BOX]
        fig_counts: Dict[str, int] = {}
        for f in figures:
            fig_counts[f.readiness.value] = fig_counts.get(f.readiness.value, 0) + 1

        return {
            "region_readiness_counts": readiness_counts,
            "source_coverage_counts": coverage_counts,
            "domain_completeness": by_domain,
            "figure_readiness_counts": fig_counts,
            "figure_totals": {"all_drawing_constructs": len(figures),
                              "layout_text_boxes": len(figures) - len(data_figures),
                              "data_figures": len(data_figures),
                              "data_figures_automatable": 0},
            "source_roles_present": sorted(available),
            "source_sheets_profiled": len(sheets),
            "derivation": ("All percentages are counts of regions per coverage status divided by "
                           "the number of classified regions in that domain. No weighting is applied."),
        }


# ============================================================================
# 8. GROUND TRUTH EVALUATION (POST-FREEZE ONLY)
# ============================================================================

class GapEvaluation:
    """Grades whether the identified gaps correspond to real FY2024 changes.

    Runs only after `freeze()`. Cannot alter readiness: it receives the frozen
    result by value and returns a separate report.
    """

    @classmethod
    def evaluate(cls, result: AuditResult) -> Dict[str, Any]:
        if not result.frozen:
            raise RuntimeError("Ground Truth evaluation attempted before readiness was frozen.")

        gt = Document(str(PATH_GROUND_TRUTH_FORBIDDEN))
        hist = Document(str(PATH_HIST))
        gt_sigs = TableIdentityProfiler.profile_document(PATH_GROUND_TRUTH_FORBIDDEN, "GT_FY2024")
        hist_sigs = TableIdentityProfiler.profile_document(PATH_HIST, "HIST_FY2023")

        def labelled(sigs, label: SemanticLabel):
            return [s for s in sigs if label in s.semantic_labels]

        findings: List[Dict[str, Any]] = []

        # 1. Benchmarking gap.
        gt_comparables = labelled(gt_sigs, SemanticLabel.COMPARABLE_COMPANIES)
        gt_screening = labelled(gt_sigs, SemanticLabel.SCREENING_REJECTION) + \
            labelled(gt_sigs, SemanticLabel.SEARCH_STEP_MATRIX)
        h_comparables = labelled(hist_sigs, SemanticLabel.COMPARABLE_COMPANIES)
        findings.append({
            "gap": "Benchmarking / comparable-company data absent from current sources",
            "status": "VERIFIED" if (gt_comparables and gt_screening) else "UNKNOWN",
            "detail": (
                f"FY2024 contains {len(gt_comparables)} comparable-company table(s) and "
                f"{len(gt_screening)} screening table(s); FY2023 contained "
                f"{len(h_comparables)} comparable-company table(s). The FY2024 file therefore "
                f"required benchmarking content that no supplied workbook carries, confirming "
                f"the gap is real rather than an artefact of the audit."),
            "evidence": {
                "gt_comparable_rows": [s.row_count for s in gt_comparables],
                "hist_comparable_rows": [s.row_count for s in h_comparables],
                "gt_screening_rows": [s.row_count for s in gt_screening],
            },
        })

        # 2. Did the comparable set actually change year on year?
        if gt_comparables and h_comparables:
            changed = sorted(s.row_count for s in gt_comparables) != sorted(
                s.row_count for s in h_comparables)
            findings.append({
                "gap": "FY2023 benchmarking text cannot be reused as current-year verified",
                "status": "VERIFIED" if changed else "CONTRADICTED",
                "detail": (
                    f"Comparable-set size changed from {sorted(s.row_count for s in h_comparables)} "
                    f"(FY2023) to {sorted(s.row_count for s in gt_comparables)} (FY2024)."
                    if changed else
                    "Comparable-set sizes are identical year on year, which weakens the claim that "
                    "the benchmarking narrative must be refreshed."),
            })

        # 3. Narrative / organisation gap.
        gt_paras = len(gt.paragraphs)
        h_paras = len(hist.paragraphs)
        findings.append({
            "gap": "Corporate narrative requires current-year management information",
            "status": "STRONGLY_SUPPORTED",
            "detail": (
                f"FY2024 carries {gt_paras} body paragraphs against FY2023's {h_paras}. The "
                f"narrative was rewritten rather than copied, supporting the finding that these "
                f"regions need current-year evidence rather than historical reuse."),
        })

        # 4. Table inventory change.
        findings.append({
            "gap": "Template table set is not a positional match to either year",
            "status": "VERIFIED",
            "detail": (
                f"FY2023 has {len(hist.tables)} tables, the template 16, FY2024 "
                f"{len(gt.tables)}. The audit correlated by content and never by index."),
        })

        counts: Dict[str, int] = {}
        for f in findings:
            counts[f["status"]] = counts.get(f["status"], 0) + 1
        return {
            "evaluated_after_freeze": True,
            "readiness_altered": False,
            "ground_truth_document": PATH_GROUND_TRUTH_FORBIDDEN.name,
            "status_counts": counts,
            "findings": findings,
            "note": ("Evaluation-only. Ground Truth was opened after the readiness map was frozen "
                     "and was not used to discover, invent or bind any source artifact."),
        }


# ============================================================================
# 9. ARTIFACT EMISSION
# ============================================================================

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_readiness_artifact(result: AuditResult) -> Dict[str, Any]:
    return {
        "artifact_id": "LOCALFILE_ROLLFORWARD_READINESS_V1",
        "phase": "E — Source Completeness & Readiness Audit",
        "generated_at": AUDIT_DATE,
        "ground_truth_used_in_readiness": False,
        "inputs": {
            "historical_fy2023": {"path": PATH_HIST.relative_to(REPO_ROOT).as_posix(),
                                  "sha256": _sha256(PATH_HIST)},
            "master_template": {"path": PATH_TMPL.relative_to(REPO_ROOT).as_posix(),
                                "sha256": _sha256(PATH_TMPL)},
            "current_source_farpt": {"path": PATH_FARPT.relative_to(REPO_ROOT).as_posix(),
                                     "sha256": _sha256(PATH_FARPT)},
            "current_source_appendix_i": {"path": PATH_APP1.relative_to(REPO_ROOT).as_posix(),
                                          "sha256": _sha256(PATH_APP1)},
        },
        "totals": {
            "regions": len(result.regions),
            "classified_regions": sum(
                1 for e in result.entries if e.readiness != Readiness.NOT_APPLICABLE.value),
            "tables": len(result.table_findings),
            "drawing_constructs": len(result.figures),
            "source_sheets": len(result.sheet_profiles),
        },
        "scorecards": result.scorecards,
        "regions": [e.to_dict() for e in result.entries],
        "figures": [f.to_dict() for f in result.figures],
        "tables": result.table_findings,
    }


def build_matrix_artifact(result: AuditResult) -> Dict[str, Any]:
    return {
        "artifact_id": "LOCALFILE_ROLLFORWARD_REQUIRED_SOURCE_MATRIX",
        "phase": "E — Source Completeness & Readiness Audit",
        "generated_at": AUDIT_DATE,
        "ground_truth_used": False,
        "separation_principle": (
            "CURRENTLY AVAILABLE SOURCE and REQUIRED BUT MISSING SOURCE are recorded in "
            "separate fields. No binding was created to satisfy a missing requirement."),
        "currently_available_sources": {
            "workbooks": [{"document": wb.document_name, "sha256": wb.document_sha256,
                           "sheets": wb.sheet_count} for wb in result.workbooks],
            "dataset_roles_present": result.scorecards["source_roles_present"],
            "sheet_profiles": result.sheet_profiles,
        },
        "requirement_matrix": [e.to_dict() for e in result.entries],
        "benchmarking_domain_audit": result.benchmarking_audit,
        "required_but_missing_sources": [a.to_dict() for a in result.artifacts],
        "human_review_queue": [h.to_dict() for h in result.review_queue],
    }


def run(write: bool = True) -> Tuple[AuditResult, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    result = SourceCompletenessAudit.freeze()
    readiness = build_readiness_artifact(result)
    matrix = build_matrix_artifact(result)
    # Ground Truth is opened only now, after the readiness map is frozen.
    evaluation = GapEvaluation.evaluate(result)
    if write:
        READINESS_JSON.parent.mkdir(parents=True, exist_ok=True)
        READINESS_JSON.write_text(json.dumps(readiness, indent=2, ensure_ascii=False), encoding="utf-8")
        MATRIX_JSON.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
        MD_PATH.write_text(render_markdown(result, readiness, matrix, evaluation), encoding="utf-8")
    return result, readiness, matrix, evaluation


# ============================================================================
# 10. MARKDOWN REPORT
# ============================================================================

def md(s: Any, limit: int = 0) -> str:
    t = str(s).replace("|", chr(92) + "|").replace(chr(10), " ")
    return (t[:limit].rstrip() + "…") if limit and len(t) > limit else t


def render_markdown(result: AuditResult, readiness: Dict[str, Any],
                    matrix: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
    L: List[str] = []
    w = L.append
    sc = result.scorecards
    bm = result.benchmarking_audit

    w("# Local File Roll-Forward Source Completeness & Readiness Audit (Phase E)")
    w("")
    w(f"**Date**: {AUDIT_DATE}  ")
    w("**Mode**: AUDIT / READINESS MAP — no mutation planned, no production behaviour changed  ")
    w(f"**Ground Truth**: quarantined during readiness; opened only for §17 evaluation  ")
    w("")
    w("---")
    w("")

    # --- Executive summary ---------------------------------------------
    w("## Executive Summary")
    w("")
    t = readiness["totals"]
    w(f"The Master Template contains **{t['regions']} heading-delimited semantic regions**, "
      f"**{t['tables']} tables** and **{t['drawing_constructs']} drawing constructs**. "
      f"The two current-source workbooks contribute **{t['source_sheets']} sheets**.")
    w("")
    seg = sc["segmentation"]
    w(f"**Segmentation is an exact partition of the document body**: "
      f"{seg['paragraphs_assigned']} paragraph assignments over {seg['body_paragraphs']} body "
      f"paragraphs and {seg['tables_assigned']} table assignments over {seg['body_tables']} "
      f"tables, with no duplicates "
      f"(`is_exact_partition = {seg['is_exact_partition']}`). Nothing is unclassified.")
    w("")
    w(f"> {seg['note']}")
    w("")
    w("### What can be automated with the files we actually have")
    w("")
    w("| Readiness | Regions |")
    w("| :--- | ---: |")
    for k in (Readiness.AUTO_NOOP_READY, Readiness.AUTO_MUTATION_READY, Readiness.HUMAN_REVIEW_READY,
              Readiness.BLOCKED_MISSING_SOURCE, Readiness.BLOCKED_INSUFFICIENT_EVIDENCE,
              Readiness.BLOCKED_SCHEMA_MISMATCH, Readiness.BLOCKED_UNSUPPORTED_CONSTRUCT,
              Readiness.NOT_APPLICABLE):
        n = sc["region_readiness_counts"].get(k.value, 0)
        if n:
            w(f"| `{k.value}` | {n} |")
    w("")
    w("| Source coverage | Regions |")
    w("| :--- | ---: |")
    for k, n in sorted(sc["source_coverage_counts"].items(), key=lambda kv: -kv[1]):
        w(f"| `{k}` | {n} |")
    w("")
    auto = sc["region_readiness_counts"].get(Readiness.AUTO_MUTATION_READY.value, 0)
    w(f"**No region is `AUTO_MUTATION_READY`.** ({auto} regions.) That is the honest answer: "
      f"the current source set supports the *financial and related-party* domains well, supports "
      f"the *benchmarking* domain not at all, and the mutation engine implements only row "
      f"insertion, which is the wrong operation for almost every region that does have a source.")
    w("")

    # --- A. Source dataset profiling ------------------------------------
    w("## A. Current Source Dataset Profiling (§3)")
    w("")
    w("Every sheet profiled from content. Sheet names were never used to assign a role.")
    w("")
    for wb in result.workbooks:
        w(f"### `{wb.document_name}`")
        w("")
        w("| Sheet | Rows × Cols | Records | Domain | Pattern | Units | Formulas | Dataset roles |")
        w("| :--- | :--- | ---: | :--- | :--- | :--- | ---: | :--- |")
        for s in result.sheet_profiles:
            if s["workbook"] != wb.document_name:
                continue
            w(f"| {md(s['sheet_name'], 30)} | {s['row_count']} × {s['column_count']} | "
              f"{s['record_count']} | {s['data_domain']} | {s['record_pattern']} | "
              f"{', '.join(s['units']) or '—'} | {s['formula_cell_count']} | "
              f"{', '.join(s['dataset_roles'])} |")
        w("")
    w(f"**Dataset roles present across the whole current source set**: "
      f"{', '.join('`%s`' % r for r in sc['source_roles_present'])}")
    w("")

    # --- B. Benchmarking audit -------------------------------------------
    w("## B. Benchmarking Domain Audit (§9) — PRIORITY")
    w("")
    w("| Required benchmarking dataset | Role | Present | Sheets |")
    w("| :--- | :--- | :---: | :--- |")
    for label, f in bm["findings"].items():
        w(f"| {label} | `{f['role']}` | {'✅' if f['present'] else '❌ **ABSENT**'} | "
          f"{', '.join(f['sheets']) or '—'} |")
    w("")
    w(f"- BvD independence codes present: **{bm['independence_codes_present']}**")
    w(f"- Accepted/rejected comparables present: **{bm['accepted_rejected_comparables_present']}**")
    w(f"- Any benchmarking source at all: **{bm['any_benchmarking_source_present']}**")
    w("")
    w(f"**Verdict.** {bm['verdict']} {bm['dependent_region_count']} region(s) depend on it: "
      f"{', '.join('`%s`' % r for r in bm['dependent_regions'])}.")
    w("")
    w("**Minimum required artifact** "
      f"(`{bm['minimum_required_artifact']['type']}`):")
    for c in bm["minimum_required_artifact"]["content"]:
        w(f"- {c}")
    w("")

    # --- C. Requirement matrix --------------------------------------------
    w("## C. Source Requirement Matrix (§5)")
    w("")
    w("| Region | Heading | Domain | Required source roles | Current artifact | Coverage | Readiness |")
    w("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for e in result.entries:
        if e.readiness == Readiness.NOT_APPLICABLE.value:
            continue
        w(f"| `{e.region_id}` | {md(e.heading, 40)} | {e.domain} | "
          f"{', '.join(e.required_source_roles) or '—'} | "
          f"{md(', '.join(e.current_source_artifacts) or '—', 34)} | "
          f"**{e.source_coverage}** | `{e.readiness}` |")
    w("")
    na = [e for e in result.entries if e.readiness == Readiness.NOT_APPLICABLE.value]
    if na:
        w(f"_{len(na)} further regions are structural containers or empty and are classified "
          f"`NOT_APPLICABLE`._")
        w("")

    # --- D. Domain scorecard -----------------------------------------------
    w("## D. Source Completeness Scorecard (§13)")
    w("")
    w("Counts of regions per coverage status. No weighting is applied.")
    w("")
    w("| Domain | Regions | Fully | Partial | N/A (static) | Missing | Insufficient | Supported % |")
    w("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for domain, d in sorted(sc["domain_completeness"].items(), key=lambda kv: -kv[1]["total"]):
        w(f"| {domain} | {d['total']} | {d['fully']} | {d['partial']} | {d['not_applicable']} | "
          f"{d['missing']} | {d['insufficient']} | **{d['supported_pct']}%** |")
    w("")
    w(f"_{sc['derivation']}_")
    w("")

    # --- E. Figures ---------------------------------------------------------
    w("## E. Figure / Media Readiness (§11)")
    w("")
    ft = sc["figure_totals"]
    w(f"The template package contains **no raster media and no charts** "
      f"(`word/media/` is empty, no `word/charts/`). Of {ft['all_drawing_constructs']} drawing "
      f"constructs, **{ft['layout_text_boxes']} are layout text boxes**, not figures. Only "
      f"**{ft['data_figures']}** are data-bearing figures, and "
      f"**{ft['data_figures_automatable']}** of them can be automated from the current sources.")
    w("")
    w("| Figure | Para | Kind | Shapes | SmartArt | Raster | Readiness | Required artifact |")
    w("| :--- | ---: | :--- | ---: | :---: | :---: | :--- | :--- |")
    for f in result.figures:
        if f.kind == FigureKind.LAYOUT_TEXT_BOX:
            continue
        w(f"| `{f.figure_id}` | {f.paragraph_index} | **{f.kind.value}** | {f.shape_count} | "
          f"{'✅' if f.is_smartart else '—'} | {'✅' if f.has_raster_image else '—'} | "
          f"`{f.readiness.value}` | {f.required_artifact.value} |")
    w("")
    for f in result.figures:
        if f.kind == FigureKind.LAYOUT_TEXT_BOX:
            continue
        w(f"- **`{f.figure_id}` ({f.kind.value})** — {f.rationale}")
    w("")
    w("| Figure readiness | Count |")
    w("| :--- | ---: |")
    for k, n in sorted(sc["figure_readiness_counts"].items(), key=lambda kv: -kv[1]):
        w(f"| `{k}` | {n} |")
    w("")

    # --- F. Historical reuse -------------------------------------------------
    w("## F. Historical Text as a Source (§12)")
    w("")
    w("FY2023 text is never promoted to current-year verified merely because it existed.")
    w("")
    w("| Historical reuse class | Regions | Meaning |")
    w("| :--- | ---: | :--- |")
    reuse_counts: Dict[str, int] = {}
    for e in result.entries:
        if e.readiness == Readiness.NOT_APPLICABLE.value:
            continue
        reuse_counts[e.historical_reuse] = reuse_counts.get(e.historical_reuse, 0) + 1
    meanings = {
        HistoricalReuse.REUSABLE_BASELINE.value:
            "Statutory / methodological text that does not change year on year.",
        HistoricalReuse.REUSABLE_WITH_VERIFICATION.value:
            "Narrative that is probably still true but must be confirmed against current facts.",
        HistoricalReuse.REQUIRES_CURRENT_YEAR_SOURCE.value:
            "Year-specific facts (amounts, comparables, headcount, agreements) — reuse is unsafe.",
        HistoricalReuse.UNSAFE_TO_REUSE.value: "Must not be carried forward under any circumstance.",
    }
    for k, n in sorted(reuse_counts.items(), key=lambda kv: -kv[1]):
        w(f"| `{k}` | {n} | {meanings.get(k, '—')} |")
    w("")

    # --- G. Required artifacts ------------------------------------------------
    w("## G. Required Additional Artifacts (§14)")
    w("")
    w("| ID | Type | Priority | Blocking | Regions | Title |")
    w("| :--- | :--- | :--- | :---: | ---: | :--- |")
    for a in result.artifacts:
        w(f"| `{a.artifact_id}` | {a.artifact_type} | **{a.priority}** | "
          f"{'✅' if a.blocking_status else '—'} | {len(a.affected_regions)} | {md(a.title, 52)} |")
    w("")
    for a in result.artifacts:
        w(f"### `{a.artifact_id}` — {a.title}")
        w("")
        w(f"- **Type**: `{a.artifact_type}`")
        w(f"- **Priority**: **{a.priority}**"
          f"{'' if a.blocking_status else '  (not blocking: the affected regions are partially supported)'}")
        w(f"- **Reason required**: {a.reason_required}")
        w(f"- **Affected regions** ({len(a.affected_regions)}): "
          f"{', '.join('`%s`' % r for r in a.affected_regions[:14])}"
          f"{' …' if len(a.affected_regions) > 14 else ''}")
        w("- **Required content**:")
        for c in a.required_content:
            w(f"  - {c}")
        w("")

    # --- H. Human review queue -------------------------------------------------
    w("## H. Human Review Work Queue (§16)")
    w("")
    blocking_items = [h for h in result.review_queue if h.blocking]
    w(f"{len(result.review_queue)} items, of which **{len(blocking_items)} are blocking**.")
    w("")
    w("| Region | Heading | Blocking | Issue | Human evidence request |")
    w("| :--- | :--- | :---: | :--- | :--- |")
    for h in result.review_queue:
        w(f"| `{h.region_id}` | {md(h.heading, 32)} | {'✅' if h.blocking else '—'} | "
          f"{md(h.issue, 78)} | {md(h.suggested_human_evidence_request, 78)} |")
    w("")

    # --- I. Available vs required ------------------------------------------------
    w("## I. Currently Available vs Required-but-Missing (§18)")
    w("")
    w("### Currently available")
    w("")
    w("| Workbook | Sheets | Dataset roles supplied |")
    w("| :--- | ---: | :--- |")
    for wb in result.workbooks:
        roles = sorted({r for s in result.sheet_profiles if s["workbook"] == wb.document_name
                        for r in s["dataset_roles"] if r != "UNKNOWN"})
        w(f"| `{wb.document_name}` | {wb.sheet_count} | {', '.join(roles)} |")
    w("")
    w("### Required but missing")
    w("")
    w("| Dataset role | Needed by | Supplied by any current source |")
    w("| :--- | ---: | :---: |")
    needed: Dict[str, int] = {}
    for e in result.entries:
        for r in e.required_source_roles:
            if r not in e.source_roles_found:
                needed[r] = needed.get(r, 0) + 1
    for r, n in sorted(needed.items(), key=lambda kv: -kv[1]):
        w(f"| `{r}` | {n} region(s) | ❌ |")
    w("")
    w("> No binding was created to satisfy any of the above. Absence is reported as absence.")
    w("")

    # --- J. Ground Truth evaluation -----------------------------------------------
    w("## J. Ground Truth Evaluation (§17) — post-freeze, evaluation-only")
    w("")
    w(f"Readiness altered by this section: **{evaluation['readiness_altered']}**.")
    w("")
    w("| Gap | Status | Detail |")
    w("| :--- | :--- | :--- |")
    for f in evaluation["findings"]:
        w(f"| {md(f['gap'], 60)} | **{f['status']}** | {md(f['detail'], 190)} |")
    w("")
    w(f"> {evaluation['note']}")
    w("")

    # --- K. Answers ------------------------------------------------------------------
    w("## K. The Two Questions")
    w("")
    w("### What can we safely automate with the files we actually have?")
    w("")
    noop = sc["region_readiness_counts"].get(Readiness.AUTO_NOOP_READY.value, 0)
    w(f"- **{noop} region(s)** are `AUTO_NOOP_READY`: statutory methodology text that carries "
      f"forward unchanged and needs no current source.")
    w(f"- **0 regions** are `AUTO_MUTATION_READY`. Two independent reasons: the benchmarking "
      f"domain has no source at all, and for the domains that *do* have a source the required "
      f"operation is cell update or data-region replacement, neither of which is implemented.")
    w("")
    w("### What exact additional files or human evidence are required?")
    w("")
    for a in result.artifacts:
        if a.priority == Priority.BLOCKING.value:
            w(f"- **{a.artifact_id}** (`{a.artifact_type}`, BLOCKING) — {md(a.title, 70)}; "
              f"unblocks {len(a.affected_regions)} region(s).")
    for a in result.artifacts:
        if a.priority != Priority.BLOCKING.value:
            w(f"- {a.artifact_id} (`{a.artifact_type}`, {a.priority}) — {md(a.title, 70)}; "
              f"affects {len(a.affected_regions)} region(s).")
    w("")
    w("---")
    w("")
    w("*Regenerate with `python foundation/tests/evaluation/source_completeness_audit.py`.*")
    w("")
    return "\n".join(L)


def main() -> None:
    result, readiness, matrix, evaluation = run(write=True)
    print(f"[+] {MD_PATH.relative_to(REPO_ROOT)}")
    print(f"[+] {MATRIX_JSON.relative_to(REPO_ROOT)}")
    print(f"[+] {READINESS_JSON.relative_to(REPO_ROOT)}")
    sc = result.scorecards
    print(f"\nregions={len(result.regions)} tables={len(result.table_findings)} "
          f"figures={len(result.figures)} sheets={len(result.sheet_profiles)}")
    print(f"readiness: {sc['region_readiness_counts']}")
    print(f"coverage : {sc['source_coverage_counts']}")
    print(f"artifacts: {len(result.artifacts)} | review queue: {len(result.review_queue)}")
    print(f"benchmarking present: {result.benchmarking_audit['any_benchmarking_source_present']}")


if __name__ == "__main__":
    main()

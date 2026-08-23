"""
Canonical Dataset Role & Evidence Policy (Phase F.1)
=====================================================
Location: foundation/applications/rollforward/evidence_policy.py

One definition, one evidence standard, one status interpretation for every
dataset role in the Roll-Forward system.

Why this exists
---------------
Phase E and Phase F disagreed about TAXPAYER_PROFILE. Both were counting
vocabulary tokens rather than checking whether the ROLE'S REQUIRED FIELDS were
actually present with values:

  * Phase E credited the role on 2 token hits, and would have credited it on
    bare column labels with no values behind them.
  * Phase F refused it because its token list said `registered address`, while
    the workbook says `Address:` (and `Địa chỉ:`) -- so it missed a field that
    is genuinely present.

The canonical rule replaces token counting with FIELD SATISFACTION: a role is
supported when its named required fields are located AND carry values, in an
artifact whose scope is authorized to supply that role.

The governing principle
-----------------------
    A document may contain information about a role without being an
    authorized current-year source for that role.

    Evidence CONTENT and evidence AUTHORITY are separate concepts.

`RoleVerdict` therefore reports both: what the content proves, and whether the
artifact was allowed to prove it.

No mutation. No Ground Truth. No network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple


# ============================================================================
# 1. SCOPES — the single canonical definition
# ============================================================================

class SupplyScope(str, Enum):
    """What part an artifact plays in the workflow."""
    HISTORICAL = "HISTORICAL"                # prior-year Local File
    TEMPLATE = "TEMPLATE"                    # master template
    CURRENT_FINANCIAL = "CURRENT_FINANCIAL"  # current-year financial workbook
    CURRENT_TAX = "CURRENT_TAX"              # current-year tax / appendix workbook
    ADDITIONAL = "ADDITIONAL"                # newly uploaded supporting artifact
    EVALUATION_ONLY = "EVALUATION_ONLY"      # Ground Truth — never a source


# Scopes that may satisfy a CURRENT-YEAR requirement, unless a role's policy
# explicitly widens or narrows this. There is no generic exception mechanism.
CURRENT_YEAR_SCOPES: FrozenSet[SupplyScope] = frozenset({
    SupplyScope.CURRENT_FINANCIAL, SupplyScope.CURRENT_TAX, SupplyScope.ADDITIONAL,
})

# Scopes that can carry historical or structural evidence but never satisfy a
# current-year requirement.
BASELINE_SCOPES: FrozenSet[SupplyScope] = frozenset({
    SupplyScope.HISTORICAL, SupplyScope.TEMPLATE,
})

FORBIDDEN_SCOPES: FrozenSet[SupplyScope] = frozenset({SupplyScope.EVALUATION_ONLY})


class EvidenceStatus(str, Enum):
    """How strongly an artifact's content supports a role."""
    VERIFIED = "VERIFIED"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class EvidenceAuthority(str, Enum):
    """Whether the artifact was ALLOWED to prove the role, independent of content."""
    CURRENT_YEAR_AUTHORITY = "CURRENT_YEAR_AUTHORITY"
    HISTORICAL_EVIDENCE_ONLY = "HISTORICAL_EVIDENCE_ONLY"
    STRUCTURAL_EVIDENCE_ONLY = "STRUCTURAL_EVIDENCE_ONLY"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"


class RoleSupport(str, Enum):
    """The canonical, single interpretation of a role's status for an artifact."""
    VERIFIED = "VERIFIED"                          # all required fields, with values, authorized
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"    # some required fields missing
    HISTORICAL_EVIDENCE = "HISTORICAL_EVIDENCE"    # content present but scope is baseline-only
    INSUFFICIENT_FIELDS = "INSUFFICIENT_FIELDS"    # below the role's minimum
    NOT_APPLICABLE = "NOT_APPLICABLE"              # scope forbidden entirely
    UNKNOWN = "UNKNOWN"                            # no evidence at all


class SchemaShape(str, Enum):
    """The structural shape a role's evidence must take."""
    TABULAR_RECORDS = "TABULAR_RECORDS"    # repeating rows under a header
    KEY_VALUE_BLOCK = "KEY_VALUE_BLOCK"    # label/value pairs (a cover block)
    NARRATIVE_TEXT = "NARRATIVE_TEXT"      # prose
    ANY = "ANY"


class DatasetRole(str, Enum):
    """The canonical dataset-role vocabulary."""
    TAXPAYER_PROFILE = "TAXPAYER_PROFILE"
    OWNERSHIP_STRUCTURE = "OWNERSHIP_STRUCTURE"
    RELATED_PARTY_TRANSACTIONS = "RELATED_PARTY_TRANSACTIONS"
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    FIXED_ASSETS = "FIXED_ASSETS"
    INTEREST_EXPENSE = "INTEREST_EXPENSE"
    TAX_SCHEDULE = "TAX_SCHEDULE"
    SEGMENTED_DATA = "SEGMENTED_DATA"
    BENCHMARKING_DATA = "BENCHMARKING_DATA"
    COMPARABLE_COMPANIES = "COMPARABLE_COMPANIES"
    IQR_RESULTS = "IQR_RESULTS"
    SCREENING_RESULTS = "SCREENING_RESULTS"
    FAR = "FAR"
    BUSINESS_NARRATIVE = "BUSINESS_NARRATIVE"
    GROUP_NARRATIVE = "GROUP_NARRATIVE"
    CONTRACTUAL_DATA = "CONTRACTUAL_DATA"
    ORGANIZATIONAL_DATA = "ORGANIZATIONAL_DATA"
    FIGURE_SOURCE = "FIGURE_SOURCE"
    # Roles already in use across Phases E/F, carried into the canonical
    # vocabulary rather than dropped so no existing verdict loses its name.
    APPENDIX_DISCLOSURE = "APPENDIX_DISCLOSURE"
    INDEPENDENCE_CODES = "INDEPENDENCE_CODES"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# 2. FIELD SPECIFICATION
# ============================================================================

@dataclass(frozen=True)
class FieldSpec:
    """One named field a role needs, with every label wording that locates it.

    Patterns are regexes over lowercased cell text. Vietnamese labels are
    included because these are Vietnamese statutory workbooks: matching only
    the English wording is how Phase F missed `Địa chỉ:` / `Address:`.
    """
    name: str
    label_patterns: Tuple[str, ...]
    required: bool = True
    value_required: bool = True
    description: str = ""

    def matches_label(self, text: str) -> bool:
        low = text.lower()
        return any(re.search(p, low) for p in self.label_patterns)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "label_patterns": list(self.label_patterns),
                "required": self.required, "value_required": self.value_required,
                "description": self.description}


@dataclass
class FieldEvidence:
    """Whether one field was located, and whether it carried a value."""
    field_name: str
    located: bool
    has_value: bool
    location: str = ""
    sample: str = ""
    value_required: bool = True

    @property
    def satisfied(self) -> bool:
        """In a key/value block a bare label proves nothing; in prose the
        mention itself is the evidence, so `value_required` decides."""
        return self.located and (self.has_value or not self.value_required)

    def to_dict(self) -> Dict[str, Any]:
        return {"field_name": self.field_name, "located": self.located,
                "has_value": self.has_value, "location": self.location,
                "value_required": self.value_required, "satisfied": self.satisfied,
                "sample": self.sample[:80]}


# ============================================================================
# 3. ROLE POLICY
# ============================================================================

@dataclass(frozen=True)
class DatasetRolePolicy:
    """The complete, single contract for one dataset role."""
    role: DatasetRole
    definition: str
    required_fields: Tuple[FieldSpec, ...]
    required_schema: SchemaShape
    allowed_supply_scopes: FrozenSet[SupplyScope]
    disallowed_supply_scopes: FrozenSet[SupplyScope]
    minimum_evidence: EvidenceStatus
    minimum_required_fields: int = 0          # 0 = every required field
    evidence_status_rules: str = ""
    # At least one discriminator must appear, or the role is refused however
    # many generic fields matched. Generic labels are ambiguous ACROSS roles:
    # a related-party register carries Name / Country / Tax code and otherwise
    # looks exactly like a comparable-company set. The discriminator is the
    # evidence only this role would carry.
    discriminator_patterns: Tuple[str, ...] = ()

    @property
    def mandatory_fields(self) -> Tuple[FieldSpec, ...]:
        return tuple(f for f in self.required_fields if f.required)

    def field_floor(self) -> int:
        return self.minimum_required_fields or len(self.mandatory_fields)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_name": self.role.value,
            "definition": self.definition,
            "required_fields": [f.to_dict() for f in self.required_fields],
            "required_schema": self.required_schema.value,
            "allowed_supply_scopes": sorted(s.value for s in self.allowed_supply_scopes),
            "disallowed_supply_scopes": sorted(s.value for s in self.disallowed_supply_scopes),
            "minimum_evidence": self.minimum_evidence.value,
            "minimum_required_fields": self.field_floor(),
            "discriminator_patterns": list(self.discriminator_patterns),
            "mandatory_field_count": len(self.mandatory_fields),
            "evidence_status_rules": self.evidence_status_rules,
        }


def _f(name: str, *patterns: str, required: bool = True, value_required: bool = True,
       description: str = "") -> FieldSpec:
    return FieldSpec(name=name, label_patterns=tuple(patterns), required=required,
                     value_required=value_required, description=description)


# Standard scope sets, so no role invents its own exception.
_CURRENT_ONLY = frozenset(CURRENT_YEAR_SCOPES)
_BASELINE_BLOCKED = frozenset(BASELINE_SCOPES | FORBIDDEN_SCOPES)

_TABULAR_RULE = (
    "VERIFIED requires every mandatory field located with a value in TABULAR_RECORDS "
    "shape and at least two data records. Prose mentioning the same words is INFERRED "
    "at best and can never be VERIFIED.")
_KV_RULE = (
    "VERIFIED requires every mandatory field located as a label with a non-empty value. "
    "A label with no value behind it does not satisfy the field.")
_NARRATIVE_RULE = (
    "A narrative role is STRONGLY_SUPPORTED at best from prose; VERIFIED requires a "
    "structured questionnaire or schedule carrying the named fields.")


ROLE_POLICIES: Dict[DatasetRole, DatasetRolePolicy] = {
    DatasetRole.TAXPAYER_PROFILE: DatasetRolePolicy(
        role=DatasetRole.TAXPAYER_PROFILE,
        definition="Identity of the taxpayer entity for the fiscal year under review.",
        required_fields=(
            _f("legal_name", r"company name", r"taxpayer name", r"tên (công ty|người nộp thuế)",
               description="registered legal name of the taxpayer"),
            _f("tax_code", r"\btax code\b", r"mã số thuế", r"enterprise code",
               description="statutory tax identification number"),
            _f("fiscal_year", r"fiscal (year|period)", r"kỳ tính thuế", r"niên độ",
               description="the fiscal year the filing covers"),
            _f("registered_address", r"\baddress\b", r"địa chỉ",
               description="registered address of the taxpayer"),
            _f("principal_activity", r"principal activity", r"main business",
               r"line of business", r"business activity", r"ngành nghề",
               description="principal business activity"),
        ),
        required_schema=SchemaShape.KEY_VALUE_BLOCK,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_KV_RULE),

    DatasetRole.OWNERSHIP_STRUCTURE: DatasetRolePolicy(
        role=DatasetRole.OWNERSHIP_STRUCTURE,
        definition="Shareholding and control relationships over the taxpayer.",
        required_fields=(
            _f("shareholder_name", r"shareholder", r"cổ đông", r"parent company", r"owner"),
            _f("ownership_percentage", r"% ?of ?ownership", r"ownership %", r"tỷ lệ sở hữu",
               r"\bownership\b"),
            _f("relationship_type", r"type of relationship", r"hình thức liên kết",
               r"relationship", required=False),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.RELATED_PARTY_TRANSACTIONS: DatasetRolePolicy(
        role=DatasetRole.RELATED_PARTY_TRANSACTIONS,
        definition="Transactions between the taxpayer and its related parties in the year.",
        required_fields=(
            _f("counterparty", r"related party", r"bên liên kết", r"counterparty"),
            _f("transaction_type", r"transaction", r"giao dịch", r"type of relationship",
               r"hình thức liên kết"),
            # `value` alone is far too generic -- a rent schedule has an
            # "Item / Value" header and would otherwise look like an RPT table.
            _f("amount", r"amount", r"giá trị", r"transaction value", r"vnd"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.FINANCIAL_STATEMENTS: DatasetRolePolicy(
        role=DatasetRole.FINANCIAL_STATEMENTS,
        definition="Audited statutory financial statements for the year under review.",
        required_fields=(
            _f("revenue", r"net sales", r"revenue", r"doanh thu"),
            _f("cost_of_sales", r"cost of goods sold", r"cost of sales", r"giá vốn"),
            _f("result", r"gross profit", r"profit before tax", r"operating profit",
               r"lợi nhuận"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.FINANCIAL_ANALYSIS: DatasetRolePolicy(
        role=DatasetRole.FINANCIAL_ANALYSIS,
        definition="Derived profit-level indicators for the tested party.",
        required_fields=(
            _f("pli_name", r"net cost plus", r"operating margin", r"return on assets",
               r"profit level indicator", r"\bncp\b"),
            _f("pli_value", r"\bebit\b", r"margin", r"ratio", r"%"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.FIXED_ASSETS: DatasetRolePolicy(
        role=DatasetRole.FIXED_ASSETS,
        definition="Fixed-asset register with cost and depreciation.",
        required_fields=(
            _f("asset_class", r"fixed asset", r"tangible asset", r"intangible asset",
               r"tài sản cố định"),
            _f("cost_or_nbv", r"historical cost", r"net book value", r"nguyên giá",
               r"accumulated depreciation", r"depreciation"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.INTEREST_EXPENSE: DatasetRolePolicy(
        role=DatasetRole.INTEREST_EXPENSE,
        definition="Interest-bearing borrowings and the interest expense on them.",
        required_fields=(
            _f("lender", r"credit institution", r"lender", r"bên cho vay", r"\bloan\b"),
            _f("interest_rate", r"interest rate", r"lãi suất", r"\binterest\b"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.TAX_SCHEDULE: DatasetRolePolicy(
        role=DatasetRole.TAX_SCHEDULE,
        definition="Corporate income tax computation for the year.",
        required_fields=(
            _f("taxable_income", r"taxable income", r"thu nhập chịu thuế",
               r"corporate income tax", r"\bcit\b"),
            _f("tax_amount", r"tax payable", r"thuế phải nộp", r"tax expense"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.SEGMENTED_DATA: DatasetRolePolicy(
        role=DatasetRole.SEGMENTED_DATA,
        definition="Financial results split by segment with an allocation basis.",
        required_fields=(
            _f("segment_name", r"segment", r"phân khúc", r"bộ phận"),
            _f("allocation_basis", r"allocation", r"allocated", r"phân bổ"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.BENCHMARKING_DATA: DatasetRolePolicy(
        role=DatasetRole.BENCHMARKING_DATA,
        definition="Output of a comparable-company search from a benchmarking database.",
        required_fields=(
            _f("database_name", r"tp catalyst", r"orbis", r"bureau van dijk", r"amadeus"),
            _f("search_date_or_version", r"version", r"search date", r"as at"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.VERIFIED,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.COMPARABLE_COMPANIES: DatasetRolePolicy(
        role=DatasetRole.COMPARABLE_COMPANIES,
        definition="The accepted set of comparable companies with their identifiers.",
        required_fields=(
            _f("company_name", r"company name", r"\bcompany\b", r"tên công ty"),
            _f("identifier", r"ticker", r"stock code", r"\btax code\b", r"mã số thuế",
               r"\bbvd\b"),
            _f("jurisdiction", r"country", r"province", r"quốc gia", r"tỉnh"),
            _f("business_description", r"business description", r"activity", r"sic code",
               r"naics", required=False),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.VERIFIED,
        evidence_status_rules=_TABULAR_RULE,
        discriminator_patterns=(r"comparable", r"sic code", r"naics", r"ticker",
                                r"stock code", r"business description", r"peer set")),

    DatasetRole.IQR_RESULTS: DatasetRolePolicy(
        role=DatasetRole.IQR_RESULTS,
        definition="Quartile statistics of the comparable set's profit level indicator.",
        required_fields=(
            _f("quartile_label", r"quartile", r"percentile", r"median", r"interquartile"),
            _f("quartile_value", r"value", r"%", r"margin", r"result", required=False),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.VERIFIED,
        minimum_required_fields=1,
        evidence_status_rules=_TABULAR_RULE),

    DatasetRole.SCREENING_RESULTS: DatasetRolePolicy(
        role=DatasetRole.SCREENING_RESULTS,
        definition="Screening steps applied to the search, with pass/reject counts.",
        required_fields=(
            _f("criterion", r"screening criteria", r"search criteria", r"criterion",
               r"reason for rejection"),
            _f("count", r"eliminated", r"retained", r"passed", r"rejected"),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.VERIFIED,
        evidence_status_rules=_TABULAR_RULE,
        discriminator_patterns=(r"screening criteria", r"reason for rejection",
                                r"search strategy", r"eliminated")),

    DatasetRole.FAR: DatasetRolePolicy(
        role=DatasetRole.FAR,
        definition="Functions performed, assets used and risks assumed in the year.",
        required_fields=(
            _f("functions", r"functions performed", r"\bfunctions\b", r"chức năng"),
            _f("assets", r"assets used", r"\bassets\b", r"tài sản"),
            _f("risks", r"risks assumed", r"\brisks\b", r"rủi ro"),
        ),
        required_schema=SchemaShape.ANY,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_NARRATIVE_RULE,
        discriminator_patterns=(r"functions performed", r"functional analysis",
                                r"risks assumed", r"phan tich chuc nang")),

    DatasetRole.BUSINESS_NARRATIVE: DatasetRolePolicy(
        role=DatasetRole.BUSINESS_NARRATIVE,
        definition="Current-year business facts: strategy, operations, restructuring.",
        required_fields=(
            _f("business_activity", r"business strategy", r"business overview",
               r"principal activity", r"operations"),
            _f("current_year_context", r"during the year", r"fiscal year", r"restructuring",
               r"market condition", required=False),
        ),
        required_schema=SchemaShape.NARRATIVE_TEXT,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        minimum_required_fields=1,
        evidence_status_rules=_NARRATIVE_RULE),

    DatasetRole.GROUP_NARRATIVE: DatasetRolePolicy(
        role=DatasetRole.GROUP_NARRATIVE,
        definition="Description of the multinational group the taxpayer belongs to.",
        required_fields=(
            _f("group_identity", r"group structure", r"ultimate parent", r"the group",
               r"master file"),
            _f("group_activity", r"group overview", r"group activities", r"worldwide",
               required=False),
        ),
        required_schema=SchemaShape.NARRATIVE_TEXT,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        minimum_required_fields=1,
        evidence_status_rules=_NARRATIVE_RULE),

    DatasetRole.CONTRACTUAL_DATA: DatasetRolePolicy(
        role=DatasetRole.CONTRACTUAL_DATA,
        definition="Executed intercompany agreements and their commercial terms.",
        required_fields=(
            _f("agreement_identity", r"\bagreement\b", r"\bcontract\b", r"hợp đồng"),
            _f("parties", r"the parties", r"between", r"bên a", r"counterparty"),
            _f("effective_date", r"effective date", r"date of signing", r"ngày hiệu lực",
               r"\bterm\b"),
        ),
        required_schema=SchemaShape.ANY,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_NARRATIVE_RULE,
        discriminator_patterns=(r"this agreement", r"the parties hereto",
                                r"effective date", r"ngày hiệu lực")),

    DatasetRole.ORGANIZATIONAL_DATA: DatasetRolePolicy(
        role=DatasetRole.ORGANIZATIONAL_DATA,
        definition="Current-year organisation structure, reporting lines and headcount.",
        required_fields=(
            _f("org_unit", r"department", r"division", r"\bdirector\b", r"phòng ban"),
            _f("reporting_or_headcount", r"reporting line", r"reports to", r"headcount",
               r"employees", r"nhân sự"),
        ),
        required_schema=SchemaShape.ANY,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        evidence_status_rules=_NARRATIVE_RULE),

    DatasetRole.FIGURE_SOURCE: DatasetRolePolicy(
        role=DatasetRole.FIGURE_SOURCE,
        definition="Structured data behind a diagram or chart (nodes, edges, series).",
        required_fields=(
            _f("series_or_node", r"\bnode\b", r"\bseries\b", r"chart data", r"figure data"),
            _f("relationship_or_value", r"\bedge\b", r"parent", r"\bvalue\b", required=False),
        ),
        required_schema=SchemaShape.TABULAR_RECORDS,
        allowed_supply_scopes=_CURRENT_ONLY,
        disallowed_supply_scopes=_BASELINE_BLOCKED,
        minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
        minimum_required_fields=1,
        evidence_status_rules=_TABULAR_RULE),
}

ROLE_POLICIES[DatasetRole.APPENDIX_DISCLOSURE] = DatasetRolePolicy(
    role=DatasetRole.APPENDIX_DISCLOSURE,
    definition="Statutory appendix / declaration schedule and its cross-references.",
    required_fields=(
        _f("declaration_identity", r"appendix", r"form 01", r"mẫu 01", r"declaration",
           r"phụ lục"),
        _f("reference", r"point of reference", r"disclosure", r"objectives", required=False),
    ),
    required_schema=SchemaShape.ANY,
    allowed_supply_scopes=_CURRENT_ONLY,
    disallowed_supply_scopes=_BASELINE_BLOCKED,
    minimum_evidence=EvidenceStatus.STRONGLY_SUPPORTED,
    minimum_required_fields=1,
    evidence_status_rules=_KV_RULE)

ROLE_POLICIES[DatasetRole.INDEPENDENCE_CODES] = DatasetRolePolicy(
    role=DatasetRole.INDEPENDENCE_CODES,
    definition="BvD independence indicators used to screen the comparable set.",
    required_fields=(
        _f("code", r"independence indicator", r"bvd independence", r"independence code",
           r"code"),
        _f("code_meaning", r"shareholder", r"ownership", r"description"),
    ),
    required_schema=SchemaShape.TABULAR_RECORDS,
    allowed_supply_scopes=_CURRENT_ONLY,
    disallowed_supply_scopes=_BASELINE_BLOCKED,
    minimum_evidence=EvidenceStatus.VERIFIED,
    evidence_status_rules=_TABULAR_RULE)

ROLE_POLICIES[DatasetRole.UNKNOWN] = DatasetRolePolicy(
    role=DatasetRole.UNKNOWN,
    definition="Sentinel for an artifact whose content proves no role.",
    required_fields=(_f("never_matches", r"(?!x)x"),),
    required_schema=SchemaShape.ANY,
    allowed_supply_scopes=frozenset(),
    disallowed_supply_scopes=frozenset(SupplyScope),
    minimum_evidence=EvidenceStatus.UNKNOWN,
    evidence_status_rules="Never satisfied; used only when no other role is.")


# ============================================================================
# 4. EVIDENCE CORPUS
# ============================================================================

@dataclass
class CorpusRow:
    """One row of observed content, with where it came from."""
    location: str
    cells: List[str]

    def joined(self) -> str:
        return " | ".join(c for c in self.cells if c)


@dataclass
class EvidenceCorpus:
    """Everything an artifact's content offers, in one uniform shape.

    Built once per artifact and reused for every role, so all roles see exactly
    the same evidence. This is what makes the policy the single interpretation.
    """
    artifact_name: str
    scope: SupplyScope
    rows: List[CorpusRow] = field(default_factory=list)
    record_count: int = 0
    has_tabular_records: bool = False
    has_narrative_text: bool = False

    def shapes(self) -> Set[SchemaShape]:
        """Every shape the corpus CONTAINS.

        An artifact is not one shape. A statutory workbook holds a key/value
        cover block AND wide record tables; demanding a single global shape
        would fail a role whose evidence is genuinely present, just in the
        other half of the file.
        """
        present: Set[SchemaShape] = set()
        wide_rows = 0
        for row in self.rows:
            populated = len(row.cells)
            if populated == 2:
                present.add(SchemaShape.KEY_VALUE_BLOCK)
            elif populated >= 3:
                wide_rows += 1
        if wide_rows >= 3 or self.has_tabular_records:
            present.add(SchemaShape.TABULAR_RECORDS)
        if self.has_narrative_text:
            present.add(SchemaShape.NARRATIVE_TEXT)
        if not present:
            present.add(SchemaShape.KEY_VALUE_BLOCK)
        return present

    def contains_shape(self, required: SchemaShape) -> bool:
        return required == SchemaShape.ANY or required in self.shapes()

    def add(self, location: str, cells: Sequence[Any]) -> None:
        norm = [re.sub(r"\s+", " ", str(c)).strip() for c in cells if c is not None]
        norm = [c for c in norm if c]
        if norm:
            self.rows.append(CorpusRow(location=location, cells=norm))

    def shape(self) -> SchemaShape:
        """The primary shape, for display. `shapes()` is what the policy uses."""
        if self.has_tabular_records:
            return SchemaShape.TABULAR_RECORDS
        if self.has_narrative_text:
            return SchemaShape.NARRATIVE_TEXT
        return SchemaShape.KEY_VALUE_BLOCK


class CorpusBuilder:
    """Turns a real artifact into an EvidenceCorpus. Content only, never the filename."""

    MAX_ROWS_PER_SHEET = 400
    MAX_PARAGRAPHS = 4000

    @classmethod
    def from_workbook(cls, path: Path, scope: SupplyScope) -> EvidenceCorpus:
        import openpyxl

        corpus = EvidenceCorpus(artifact_name=path.name, scope=scope)
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        try:
            tabular_records = 0
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows_seen = 0
                populated = 0
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i >= cls.MAX_ROWS_PER_SHEET:
                        break
                    corpus.add(f"{path.name}!{sheet_name}!r{i + 1}", row)
                    rows_seen += 1
                    if sum(1 for c in row if c is not None and str(c).strip()) >= 2:
                        populated += 1
                if populated >= 3:
                    corpus.has_tabular_records = True
                    tabular_records += max(populated - 1, 0)
            corpus.record_count = tabular_records
        finally:
            wb.close()
        return corpus

    @classmethod
    def from_document(cls, path: Path, scope: SupplyScope) -> EvidenceCorpus:
        from docx import Document

        corpus = EvidenceCorpus(artifact_name=path.name, scope=scope)
        doc = Document(str(path))

        long_paragraphs = 0
        for i, para in enumerate(doc.paragraphs[:cls.MAX_PARAGRAPHS]):
            text = re.sub(r"\s+", " ", para.text or "").strip()
            if not text:
                continue
            corpus.add(f"{path.name}!p{i + 1}", [text])
            if len(text) > 80:
                long_paragraphs += 1

        records = 0
        for t_idx, table in enumerate(doc.tables):
            for r_idx, row in enumerate(table.rows):
                corpus.add(f"{path.name}!t{t_idx}r{r_idx}", [c.text for c in row.cells])
            if len(table.rows) >= 3:
                corpus.has_tabular_records = True
                records += len(table.rows) - 1

        corpus.record_count = records
        corpus.has_narrative_text = long_paragraphs >= 3 and not corpus.has_tabular_records
        return corpus

    @classmethod
    def from_rows(cls, name: str, scope: SupplyScope,
                  rows: Sequence[Sequence[Any]], location: str = "rows") -> EvidenceCorpus:
        """For tests and in-memory evidence."""
        corpus = EvidenceCorpus(artifact_name=name, scope=scope)
        populated = 0
        for i, row in enumerate(rows):
            corpus.add(f"{location}!r{i + 1}", row)
            if sum(1 for c in row if c is not None and str(c).strip()) >= 2:
                populated += 1
        if populated >= 3:
            corpus.has_tabular_records = True
            corpus.record_count = max(populated - 1, 0)
        return corpus


# ============================================================================
# 5. VERDICT
# ============================================================================

@dataclass
class RoleVerdict:
    """The single canonical answer for one (artifact, role) pair."""
    role: DatasetRole
    artifact_name: str
    scope: SupplyScope
    support: RoleSupport
    evidence_status: EvidenceStatus
    authority: EvidenceAuthority
    fields: List[FieldEvidence] = field(default_factory=list)
    satisfied_fields: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    observed_shape: SchemaShape = SchemaShape.ANY
    rationale: str = ""

    @property
    def can_satisfy_current_year(self) -> bool:
        """Content AND authority must both hold."""
        return (self.support == RoleSupport.VERIFIED
                and self.authority == EvidenceAuthority.CURRENT_YEAR_AUTHORITY)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value, "artifact": self.artifact_name,
            "scope": self.scope.value, "support": self.support.value,
            "evidence_status": self.evidence_status.value, "authority": self.authority.value,
            "satisfied_fields": self.satisfied_fields, "missing_fields": self.missing_fields,
            "observed_shape": self.observed_shape.value,
            "can_satisfy_current_year": self.can_satisfy_current_year,
            "fields": [f.to_dict() for f in self.fields],
            "rationale": self.rationale,
        }


# ============================================================================
# 6. POLICY ENGINE
# ============================================================================

class EvidencePolicyEngine:
    """The one place a dataset role is decided. Deterministic and field-based."""

    MIN_TABULAR_RECORDS = 2

    @classmethod
    def policy_for(cls, role: DatasetRole) -> DatasetRolePolicy:
        return ROLE_POLICIES[role]

    @classmethod
    def authority_for(cls, policy: DatasetRolePolicy, scope: SupplyScope) -> EvidenceAuthority:
        """Authority depends only on scope and the role's declared scope sets."""
        if scope in policy.disallowed_supply_scopes:
            if scope == SupplyScope.HISTORICAL:
                return EvidenceAuthority.HISTORICAL_EVIDENCE_ONLY
            if scope == SupplyScope.TEMPLATE:
                return EvidenceAuthority.STRUCTURAL_EVIDENCE_ONLY
            return EvidenceAuthority.NOT_AUTHORIZED
        if scope in policy.allowed_supply_scopes:
            return EvidenceAuthority.CURRENT_YEAR_AUTHORITY
        return EvidenceAuthority.NOT_AUTHORIZED

    @staticmethod
    def value_is_required(policy: "DatasetRolePolicy", spec: FieldSpec) -> bool:
        """A label with no value proves nothing in a key/value block or a table.

        In prose there are no label:value pairs -- the mention itself is the
        evidence -- so narrative-shaped roles do not demand one. The rule is
        stated once here rather than repeated on every field.
        """
        if policy.required_schema == SchemaShape.KEY_VALUE_BLOCK:
            # A cover block states "Tax code | 0201824857". A bare label proves
            # nothing, so the value must sit beside it.
            return spec.value_required
        # In a table the value lives in the rows BELOW the column header, and in
        # prose there is no label:value pair at all. Presence of the column or
        # the mention is the field evidence; that the table actually has data is
        # checked separately by the record-count rule.
        return False

    @classmethod
    def locate_field(cls, spec: FieldSpec, corpus: EvidenceCorpus,
                     value_required: Optional[bool] = None) -> FieldEvidence:
        """Finds a field's label and decides whether a value sits behind it."""
        needs_value = spec.value_required if value_required is None else value_required
        best = FieldEvidence(field_name=spec.name, located=False, has_value=False,
                             value_required=needs_value)
        for row in corpus.rows:
            for idx, cell in enumerate(row.cells):
                if not spec.matches_label(cell):
                    continue
                # A value is the next non-empty cell on the row, or trailing text
                # in the same cell after a colon ("Company name:  ACME Ltd").
                value = ""
                if idx + 1 < len(row.cells):
                    value = row.cells[idx + 1]
                if not value and ":" in cell:
                    value = cell.split(":", 1)[1].strip()
                has_value = bool(value) and value.lower() != cell.lower()
                evidence = FieldEvidence(
                    field_name=spec.name, located=True, has_value=has_value,
                    location=row.location, sample=(value or cell),
                    value_required=needs_value)
                if evidence.satisfied:
                    return evidence
                best = evidence
        return best

    @classmethod
    def evaluate(cls, role: DatasetRole, corpus: EvidenceCorpus) -> RoleVerdict:
        """The canonical evaluation. Same inputs always give the same verdict."""
        policy = cls.policy_for(role)
        authority = cls.authority_for(policy, corpus.scope)
        shape = corpus.shape()

        discriminator_hit = cls._discriminator_hit(policy, corpus)
        fields = [cls.locate_field(spec, corpus, cls.value_is_required(policy, spec))
                  for spec in policy.required_fields]
        mandatory = {f.name for f in policy.mandatory_fields}
        satisfied = [f.field_name for f in fields
                     if f.satisfied or (not _spec_required(policy, f.field_name) and f.located)]
        satisfied_mandatory = [f.field_name for f in fields
                               if f.field_name in mandatory and f.satisfied]
        missing = sorted(mandatory - set(satisfied_mandatory))

        floor = policy.field_floor()
        count = len(satisfied_mandatory)

        # ---- content verdict, independent of authority -------------------
        if policy.discriminator_patterns and not discriminator_hit:
            support = RoleSupport.INSUFFICIENT_FIELDS
            status = EvidenceStatus.UNKNOWN
            rationale = (
                "No discriminating evidence for " + role.value + ". Its generic fields also "
                "match other roles' data, so the role requires one of "
                + str(list(policy.discriminator_patterns)[:4]) + " and found none.")
        elif count == 0:
            support = RoleSupport.UNKNOWN
            status = EvidenceStatus.UNKNOWN
            rationale = f"No mandatory field of {role.value} was located with a value."
        elif count < floor:
            support = RoleSupport.PARTIALLY_SUPPORTED
            status = EvidenceStatus.INFERRED
            rationale = (f"{count} of {len(mandatory)} mandatory field(s) satisfied "
                         f"({', '.join(satisfied_mandatory)}); missing {', '.join(missing)}.")
        else:
            shape_ok = corpus.contains_shape(policy.required_schema)
            records_ok = (policy.required_schema != SchemaShape.TABULAR_RECORDS
                          or corpus.record_count >= cls.MIN_TABULAR_RECORDS)
            if shape_ok and records_ok:
                support = RoleSupport.VERIFIED
                status = EvidenceStatus.VERIFIED
                rationale = (f"All {len(mandatory)} mandatory field(s) located with values in "
                             f"{shape.value} shape over {corpus.record_count} record(s).")
            else:
                support = RoleSupport.PARTIALLY_SUPPORTED
                status = EvidenceStatus.STRONGLY_SUPPORTED
                reasons = []
                if not shape_ok:
                    reasons.append(
                        f"the corpus contains {sorted(x.value for x in corpus.shapes())} "
                        f"but the role requires {policy.required_schema.value}")
                if not records_ok:
                    reasons.append(f"only {corpus.record_count} record(s), "
                                   f"{cls.MIN_TABULAR_RECORDS} required")
                rationale = (f"All mandatory fields present, but {'; '.join(reasons)}. "
                             f"The role cannot be VERIFIED on this shape.")

        # ---- authority overrides the SUPPORT, never the content ----------
        if authority == EvidenceAuthority.NOT_AUTHORIZED:
            support = RoleSupport.NOT_APPLICABLE
            rationale = (f"{corpus.scope.value} is forbidden from supplying any role. "
                         f"Content observation: {rationale}")
        elif authority in (EvidenceAuthority.HISTORICAL_EVIDENCE_ONLY,
                           EvidenceAuthority.STRUCTURAL_EVIDENCE_ONLY) \
                and support in (RoleSupport.VERIFIED, RoleSupport.PARTIALLY_SUPPORTED):
            support = RoleSupport.HISTORICAL_EVIDENCE
            rationale = (
                f"Content supports {role.value}, but {corpus.scope.value} carries "
                f"{authority.value.lower().replace('_', ' ')} and may not satisfy a "
                f"current-year requirement. Observation: {rationale}")

        return RoleVerdict(
            role=role, artifact_name=corpus.artifact_name, scope=corpus.scope,
            support=support, evidence_status=status, authority=authority,
            fields=fields, satisfied_fields=satisfied_mandatory, missing_fields=missing,
            observed_shape=shape, rationale=rationale)

    @classmethod
    def _discriminator_hit(cls, policy: DatasetRolePolicy, corpus: EvidenceCorpus) -> bool:
        if not policy.discriminator_patterns:
            return True
        for row in corpus.rows:
            joined = row.joined().lower()
            if any(re.search(pat, joined) for pat in policy.discriminator_patterns):
                return True
        return False

    @classmethod
    def evaluate_all(cls, corpus: EvidenceCorpus) -> Dict[DatasetRole, RoleVerdict]:
        return {role: cls.evaluate(role, corpus) for role in DatasetRole}

    @classmethod
    def current_year_roles(cls, corpus: EvidenceCorpus) -> List[DatasetRole]:
        return sorted(
            (r for r, v in cls.evaluate_all(corpus).items() if v.can_satisfy_current_year),
            key=lambda r: r.value)


def _spec_required(policy: DatasetRolePolicy, field_name: str) -> bool:
    for f in policy.required_fields:
        if f.name == field_name:
            return f.required
    return True


def policy_compatibility_matrix() -> Dict[str, Any]:
    """Which scope may supply which role, for the report."""
    return {
        "scopes": [s.value for s in SupplyScope],
        "current_year_scopes": sorted(s.value for s in CURRENT_YEAR_SCOPES),
        "baseline_scopes": sorted(s.value for s in BASELINE_SCOPES),
        "forbidden_scopes": sorted(s.value for s in FORBIDDEN_SCOPES),
        "matrix": {
            role.value: {
                scope.value: EvidencePolicyEngine.authority_for(policy, scope).value
                for scope in SupplyScope
            }
            for role, policy in ROLE_POLICIES.items()
        },
        "roles": {role.value: policy.to_dict() for role, policy in ROLE_POLICIES.items()},
    }

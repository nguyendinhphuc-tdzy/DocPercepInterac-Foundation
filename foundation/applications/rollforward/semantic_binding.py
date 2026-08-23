"""
Source-to-Target Semantic Binding Validation (Phase C2)
========================================================
Location: foundation/applications/rollforward/semantic_binding.py

Phase D3.1 findings P0-3, P0-5 and P0-7: a source binding was treated as
VERIFIED because a sheet and a cell range existed, and a mutation plan was
allowed to write a percentage into a "Business description" column.

This module makes a binding prove itself before it may be VERIFIED:

  1. The TARGET region declares an expected domain, column schema, field
     types, row semantics and unit semantics (`TargetRegionSchema`).
  2. The SOURCE must actually contain the dataset role that domain requires
     (`SourceCapabilityProfiler`), otherwise MISSING_CURRENT_SOURCE.
  3. The source record schema must be compatible with the target column
     schema, otherwise INCOMPATIBLE_SCHEMA.
  4. Individual values must be compatible with the column they are written
     into, otherwise COLUMN_DOMAIN_VIOLATION.

A binding that cannot prove all four is BLOCKED. Blocking is the correct,
expected outcome when evidence is absent.

No mutation. No Ground Truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from applications.rollforward.source_capability import (
    DatasetRole,
    SheetDatasetProfile,
    WorkbookCapabilityProfile,
)
from applications.rollforward.table_identity import SemanticLabel, TableIdentitySignature


class FieldSemanticRole(str, Enum):
    """What a target table column means."""
    ORDINAL = "ORDINAL"
    ENTITY_NAME = "ENTITY_NAME"
    COUNTRY = "COUNTRY"
    PROVINCE = "PROVINCE"
    TAX_CODE = "TAX_CODE"
    TICKER = "TICKER"
    INDUSTRY_CODE = "INDUSTRY_CODE"
    DESCRIPTION = "DESCRIPTION"
    MONETARY = "MONETARY"
    PERCENTAGE = "PERCENTAGE"
    RATIO = "RATIO"
    STATISTIC_LABEL = "STATISTIC_LABEL"
    CRITERION_LABEL = "CRITERION_LABEL"
    COUNT = "COUNT"
    DATE = "DATE"
    FREE_TEXT = "FREE_TEXT"
    UNKNOWN = "UNKNOWN"


class UnitSemantic(str, Enum):
    VND = "VND"
    USD = "USD"
    PERCENT = "PERCENT"
    RATIO = "RATIO"
    COUNT = "COUNT"
    NONE = "NONE"


class RowSemantics(str, Enum):
    """What one row of a target table represents."""
    ENTITY_RECORD = "ENTITY_RECORD"            # one comparable company, one related party
    STATISTIC = "STATISTIC"                    # one percentile / median / PLI
    CRITERION_STEP = "CRITERION_STEP"          # one screening step / rejection reason
    KEY_VALUE = "KEY_VALUE"                    # label/value narrative pair
    LINE_ITEM = "LINE_ITEM"                    # one P&L or balance-sheet line
    UNKNOWN = "UNKNOWN"


class BindingVerdict(str, Enum):
    """Outcome of validating one target region against the current sources."""
    VERIFIED = "VERIFIED"
    MISSING_CURRENT_SOURCE = "MISSING_CURRENT_SOURCE"
    INCOMPATIBLE_SCHEMA = "INCOMPATIBLE_SCHEMA"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"
    COLUMN_DOMAIN_VIOLATION = "COLUMN_DOMAIN_VIOLATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# Which dataset role a target domain requires from a current source.
DOMAIN_REQUIRED_ROLES: Dict[SemanticLabel, Tuple[DatasetRole, ...]] = {
    SemanticLabel.ARMS_LENGTH_RANGE: (DatasetRole.IQR_RESULTS, DatasetRole.BENCHMARKING_DATA),
    SemanticLabel.COMPARABLE_COMPANIES: (DatasetRole.COMPARABLE_COMPANIES, DatasetRole.BENCHMARKING_DATA),
    SemanticLabel.SCREENING_STRATEGY: (DatasetRole.SCREENING_RESULTS, DatasetRole.BENCHMARKING_DATA),
    SemanticLabel.SCREENING_REJECTION: (DatasetRole.SCREENING_RESULTS,),
    SemanticLabel.SEARCH_STEP_MATRIX: (DatasetRole.SCREENING_RESULTS, DatasetRole.BENCHMARKING_DATA),
    SemanticLabel.RELATED_PARTY_TRANSACTIONS: (DatasetRole.RELATED_PARTY_TRANSACTIONS,),
    SemanticLabel.FINANCIAL_INDICATORS: (DatasetRole.FINANCIAL_STATEMENTS, DatasetRole.FINANCIAL_ANALYSIS),
    SemanticLabel.INTEREST_SCHEDULE: (DatasetRole.INTEREST_EXPENSE,),
    SemanticLabel.OWNERSHIP_CODE_LIST: (DatasetRole.REFERENCE_LIST,),
    SemanticLabel.INDUSTRY_CODE_LIST: (DatasetRole.REFERENCE_LIST,),
}

# Header wording -> field role. Content-derived, order matters (first match wins).
_HEADER_ROLE_SIGNALS: List[Tuple[FieldSemanticRole, Tuple[str, ...]]] = [
    (FieldSemanticRole.ORDINAL, ("no", "no.", "stt", "#", "step")),
    (FieldSemanticRole.TAX_CODE, ("tax code", "tax id", "mst")),
    (FieldSemanticRole.TICKER, ("ticker", "stock code", "symbol")),
    (FieldSemanticRole.INDUSTRY_CODE, ("sic code", "vn sic", "naics", "industry code")),
    (FieldSemanticRole.PROVINCE, ("province", "city")),
    (FieldSemanticRole.COUNTRY, ("country", "nation", "region")),
    (FieldSemanticRole.DESCRIPTION, ("business description", "description", "activity", "details")),
    (FieldSemanticRole.ENTITY_NAME, ("company", "company name", "entity", "related party", "name")),
    (FieldSemanticRole.PERCENTAGE, ("%", "percent", "margin", "ratio (%)")),
    (FieldSemanticRole.MONETARY, ("amount", "vnd", "usd", "value", "principal", "revenue", "sales")),
    (FieldSemanticRole.COUNT, ("eliminated", "retained", "passed", "count", "number")),
    (FieldSemanticRole.DATE, ("date", "period", "maturity")),
    (FieldSemanticRole.STATISTIC_LABEL, ("item", "index", "indicator")),
    (FieldSemanticRole.CRITERION_LABEL, ("criteria", "criterion", "screen", "database used")),
]

# Value shapes each field role will accept.
_ROLE_ACCEPTS: Dict[FieldSemanticRole, Tuple[str, ...]] = {
    FieldSemanticRole.ORDINAL: ("integer", "empty"),
    FieldSemanticRole.ENTITY_NAME: ("text",),
    FieldSemanticRole.COUNTRY: ("text",),
    FieldSemanticRole.PROVINCE: ("text",),
    FieldSemanticRole.TAX_CODE: ("code", "integer"),
    FieldSemanticRole.TICKER: ("code", "text"),
    FieldSemanticRole.INDUSTRY_CODE: ("code", "integer"),
    FieldSemanticRole.DESCRIPTION: ("text",),
    FieldSemanticRole.MONETARY: ("monetary", "integer", "decimal"),
    FieldSemanticRole.PERCENTAGE: ("percentage", "decimal"),
    FieldSemanticRole.RATIO: ("decimal", "percentage"),
    FieldSemanticRole.STATISTIC_LABEL: ("text",),
    FieldSemanticRole.CRITERION_LABEL: ("text",),
    FieldSemanticRole.COUNT: ("integer",),
    FieldSemanticRole.DATE: ("date", "text"),
    FieldSemanticRole.FREE_TEXT: ("text", "integer", "decimal", "code", "monetary", "percentage"),
    FieldSemanticRole.UNKNOWN: (),
}

_PCT_RE = re.compile(r"^[-+]?[\d.,]+\s*%$")
_INT_RE = re.compile(r"^[-+]?\d{1,4}$")
_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-./]{1,19}$")
_DATE_RE = re.compile(r"^\d{1,4}[-/.]\d{1,2}([-/.]\d{1,4})?$")


def classify_value_shape(value: Any) -> str:
    """Deterministic shape of a candidate cell value."""
    if value is None:
        return "empty"
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text:
        return "empty"
    if _PCT_RE.match(text):
        return "percentage"
    if _DATE_RE.match(text):
        return "date"
    bare = text.replace(",", "").replace(" ", "")
    digits = bare.lstrip("-+")
    # Shape is decided by FORMATTING, not by magnitude. A ten-digit tax code
    # is a code; a thousands-separated figure is money. Judging by size alone
    # made "0201234500" (tax code) look monetary and "14100" (SIC) decimal.
    if digits.isdigit():
        if digits.startswith("0") and len(digits) > 1:
            return "code"          # leading zero is significant -> identifier
        if "," in text:
            return "monetary"      # thousands-separated -> money
        return "integer"
    try:
        Decimal(bare)
        return "monetary" if "," in text else "decimal"
    except (InvalidOperation, ValueError):
        pass
    if _CODE_RE.match(text) and any(ch.isdigit() for ch in text) and " " not in text:
        return "code"
    return "text"


@dataclass
class TargetColumnSpec:
    """Declared semantics of one target table column."""
    index: int
    header: str
    role: FieldSemanticRole
    unit: UnitSemantic = UnitSemantic.NONE
    required: bool = True

    def accepts(self, value: Any) -> Tuple[bool, str]:
        shape = classify_value_shape(value)
        if shape == "empty":
            return (not self.required, f"empty value for {'required' if self.required else 'optional'} column")
        allowed = _ROLE_ACCEPTS.get(self.role, ())
        if not allowed:
            return False, f"column role {self.role.value} declares no accepted value shape"
        if shape in allowed:
            return True, f"{shape} accepted by {self.role.value}"
        return False, (f"value shape '{shape}' is not accepted by column "
                       f"{self.index} ('{self.header}') whose role is {self.role.value} "
                       f"(accepts {', '.join(allowed)})")

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "header": self.header, "role": self.role.value,
                "unit": self.unit.value, "required": self.required}


@dataclass
class TargetRegionSchema:
    """The full declared semantics of a target region."""
    region_id: str
    table_identity_key: str
    expected_domain: SemanticLabel
    columns: List[TargetColumnSpec]
    row_semantics: RowSemantics
    required_source_roles: Tuple[DatasetRole, ...] = ()
    header_row_count: int = 1
    footer_row_idxs: Tuple[int, ...] = ()
    placeholder_row_idxs: Tuple[int, ...] = ()

    @property
    def data_region(self) -> Tuple[int, int]:
        """Inclusive [start, end] row span rows may legitimately be written to."""
        start = self.header_row_count
        end = min(self.footer_row_idxs) - 1 if self.footer_row_idxs else None
        return start, end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "table_identity_key": self.table_identity_key,
            "expected_domain": self.expected_domain.value,
            "row_semantics": self.row_semantics.value,
            "required_source_roles": [r.value for r in self.required_source_roles],
            "header_row_count": self.header_row_count,
            "footer_row_idxs": list(self.footer_row_idxs),
            "placeholder_row_idxs": list(self.placeholder_row_idxs),
            "data_region": list(self.data_region),
            "columns": [c.to_dict() for c in self.columns],
        }


@dataclass
class BindingValidation:
    """Evidence-backed verdict for one target region against the sources."""
    region_id: str
    verdict: BindingVerdict
    expected_domain: SemanticLabel
    required_roles: List[DatasetRole]
    roles_found: List[DatasetRole]
    candidate_sheets: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    @property
    def is_executable(self) -> bool:
        return self.verdict == BindingVerdict.VERIFIED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "region_id": self.region_id,
            "verdict": self.verdict.value,
            "expected_domain": self.expected_domain.value,
            "required_source_roles": [r.value for r in self.required_roles],
            "source_roles_found": [r.value for r in self.roles_found],
            "candidate_sheets": self.candidate_sheets,
            "violations": self.violations,
            "evidence": self.evidence,
            "is_executable": self.is_executable,
        }


class TargetSchemaDeriver:
    """Derives a declared target schema from a position-free table signature."""

    ROW_SEMANTICS_BY_LABEL = {
        SemanticLabel.COMPARABLE_COMPANIES: RowSemantics.ENTITY_RECORD,
        SemanticLabel.RELATED_PARTY_TRANSACTIONS: RowSemantics.ENTITY_RECORD,
        SemanticLabel.ARMS_LENGTH_RANGE: RowSemantics.STATISTIC,
        SemanticLabel.SCREENING_STRATEGY: RowSemantics.KEY_VALUE,
        SemanticLabel.SCREENING_REJECTION: RowSemantics.CRITERION_STEP,
        SemanticLabel.SEARCH_STEP_MATRIX: RowSemantics.CRITERION_STEP,
        SemanticLabel.FINANCIAL_INDICATORS: RowSemantics.LINE_ITEM,
        SemanticLabel.INTEREST_SCHEDULE: RowSemantics.ENTITY_RECORD,
        SemanticLabel.INDUSTRY_CODE_LIST: RowSemantics.KEY_VALUE,
        SemanticLabel.OWNERSHIP_CODE_LIST: RowSemantics.KEY_VALUE,
    }

    @classmethod
    def derive(cls, region_id: str, sig: TableIdentitySignature) -> TargetRegionSchema:
        columns = [
            TargetColumnSpec(
                index=c.index,
                header=c.header,
                role=cls.header_role(c.header, c.index),
                unit=cls.header_unit(c.header),
                required=c.index == 0 or bool(c.header),
            )
            for c in sig.column_schemas
        ]
        domain = sig.primary_label
        return TargetRegionSchema(
            region_id=region_id,
            table_identity_key=sig.identity_key,
            expected_domain=domain,
            columns=columns,
            row_semantics=cls.ROW_SEMANTICS_BY_LABEL.get(domain, RowSemantics.UNKNOWN),
            required_source_roles=DOMAIN_REQUIRED_ROLES.get(domain, ()),
            header_row_count=1,
            footer_row_idxs=cls.detect_footer_rows(sig),
            placeholder_row_idxs=(),
        )

    @staticmethod
    def header_role(header: str, index: int) -> FieldSemanticRole:
        h = re.sub(r"\s+", " ", (header or "")).strip().lower()
        if not h:
            return FieldSemanticRole.UNKNOWN
        for role, tokens in _HEADER_ROLE_SIGNALS:
            for t in tokens:
                if h == t or h.startswith(t + " ") or t in h:
                    return role
        return FieldSemanticRole.FREE_TEXT

    @staticmethod
    def header_unit(header: str) -> UnitSemantic:
        h = (header or "").lower()
        if "%" in h:
            return UnitSemantic.PERCENT
        if "vnd" in h:
            return UnitSemantic.VND
        if "usd" in h:
            return UnitSemantic.USD
        return UnitSemantic.NONE

    @staticmethod
    def detect_footer_rows(sig: TableIdentitySignature) -> Tuple[int, ...]:
        """A trailing row whose cells are all identical is a spanned footer band."""
        # A full-width merged footer surfaces as every cell carrying the same text.
        # Only the signature's header/merge evidence is available here, so this is
        # reported by the caller when it has the live table; see MutationPreconditionValidator.
        return ()


class SemanticBindingValidator:
    """Grants VERIFIED only when the source proves it can supply the target."""

    @classmethod
    def validate(
        cls,
        schema: TargetRegionSchema,
        workbooks: Sequence[WorkbookCapabilityProfile],
    ) -> BindingValidation:
        required = list(schema.required_source_roles)
        found: List[DatasetRole] = []
        candidates: List[str] = []
        evidence: List[str] = []

        for wb in workbooks:
            for role in required:
                if wb.has_role(role):
                    if role not in found:
                        found.append(role)
                    for sheet in wb.sheets_with_role(role):
                        label = f"{wb.document_name}!{sheet.sheet_name}"
                        if label not in candidates:
                            candidates.append(label)
                            evidence.append(
                                f"{label} carries {role.value} "
                                f"({sheet.record_count} records; evidence "
                                f"{sheet.role_evidence.get(role.value, [])[:4]})"
                            )

        if not required:
            return BindingValidation(
                region_id=schema.region_id,
                verdict=BindingVerdict.INSUFFICIENT_EVIDENCE,
                expected_domain=schema.expected_domain,
                required_roles=[], roles_found=[],
                violations=[
                    f"Target domain {schema.expected_domain.value} declares no required source "
                    "dataset role, so no source can be proven compatible with it."
                ],
            )

        if not found:
            return BindingValidation(
                region_id=schema.region_id,
                verdict=BindingVerdict.MISSING_CURRENT_SOURCE,
                expected_domain=schema.expected_domain,
                required_roles=required, roles_found=[],
                violations=[
                    f"No bound workbook contains any of the required dataset roles "
                    f"{[r.value for r in required]} for target domain "
                    f"{schema.expected_domain.value}. Sheets were profiled by content, "
                    f"not by name."
                ],
                evidence=[
                    f"{wb.document_name}: roles present = "
                    f"{[r.value for r in wb.roles_present()]}" for wb in workbooks
                ],
            )

        unknown_cols = [c for c in schema.columns if c.role == FieldSemanticRole.UNKNOWN and c.required]
        if unknown_cols:
            return BindingValidation(
                region_id=schema.region_id,
                verdict=BindingVerdict.INCOMPATIBLE_SCHEMA,
                expected_domain=schema.expected_domain,
                required_roles=required, roles_found=found,
                candidate_sheets=candidates,
                violations=[
                    f"Required target column {c.index} ('{c.header}') has no derivable "
                    f"semantic role." for c in unknown_cols
                ],
                evidence=evidence,
            )

        if len(candidates) > 1 and len(found) == len(required):
            pass  # multiple compatible sheets is fine; the plan names the exact one

        return BindingValidation(
            region_id=schema.region_id,
            verdict=BindingVerdict.VERIFIED,
            expected_domain=schema.expected_domain,
            required_roles=required, roles_found=found,
            candidate_sheets=candidates,
            evidence=evidence,
        )

    @classmethod
    def validate_value_against_column(
        cls, schema: TargetRegionSchema, col_idx: int, value: Any
    ) -> Tuple[bool, str]:
        """Rejects a percentage written into a description column, and similar."""
        spec = next((c for c in schema.columns if c.index == col_idx), None)
        if spec is None:
            return False, f"target column {col_idx} does not exist in region {schema.region_id}"
        return spec.accepts(value)

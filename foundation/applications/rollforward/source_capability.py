"""
Current-Source Dataset Capability Profiling (Phase C2)
=======================================================
Location: foundation/applications/rollforward/source_capability.py

Phase D3.1 finding P0-5: benchmarking regions were marked READY against
workbooks that contain no benchmarking data at all. Source EXISTENCE was
treated as source COMPATIBILITY.

This module answers, from content rather than from sheet names:

    What datasets does this workbook actually contain?

For every sheet it derives a header row, a record schema, a data domain, unit
semantics, formula usage and a true record count, then assigns dataset roles
from the observed content. A sheet called "Financial Analysis" earns
FINANCIAL_ANALYSIS only if its cells look like financial analysis, and it can
never earn BENCHMARKING_DATA by name alone.

The workbook-level profile exposes `has_role()` so a binding validator can ask
"does this workbook contain comparable-company records?" and get an
evidence-backed answer.

No mutation. No Ground Truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import openpyxl

MAX_SCAN_ROWS = 400          # bound the scan on very large sheets
HEADER_SEARCH_DEPTH = 12     # header rows rarely sit deeper than this


class DatasetRole(str, Enum):
    """A dataset a Local File roll-forward may need from a current source."""
    RELATED_PARTY_TRANSACTIONS = "RPT_DATA"
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    FINANCIAL_ANALYSIS = "FINANCIAL_ANALYSIS"
    FIXED_ASSETS = "FIXED_ASSETS"
    BENCHMARKING_DATA = "BENCHMARKING_DATA"
    COMPARABLE_COMPANIES = "COMPARABLE_COMPANIES"
    IQR_RESULTS = "IQR_RESULTS"
    SCREENING_RESULTS = "SCREENING_RESULTS"
    NARRATIVE_DISCLOSURE = "NARRATIVE_DISCLOSURE"
    RELATED_PARTIES_REGISTER = "RELATED_PARTIES_REGISTER"
    INTEREST_EXPENSE = "INTEREST_EXPENSE"
    SEGMENTED_DATA = "SEGMENTED_DATA"
    REFERENCE_LIST = "REFERENCE_LIST"
    CHECKLIST = "CHECKLIST"
    UNKNOWN = "UNKNOWN"


class DataDomain(str, Enum):
    """Coarse domain of the values a sheet carries."""
    MONETARY = "MONETARY"
    RATIO = "RATIO"
    ENTITY = "ENTITY"
    NARRATIVE = "NARRATIVE"
    REFERENCE = "REFERENCE"
    MIXED = "MIXED"
    EMPTY = "EMPTY"


# Content signals -> role. Each entry: (role, required token hits, tokens).
# Tokens are matched against the HEADER ROW and the LEFTMOST LABEL COLUMN,
# i.e. against data, never against the sheet's name.
_ROLE_SIGNALS: List[Tuple[DatasetRole, int, Sequence[str]]] = [
    (DatasetRole.COMPARABLE_COMPANIES, 3, (
        "company name", "ticker", "tax code", "sic code", "naics", "business description",
        "province", "comparable", "stock code", "bvd", "independence indicator")),
    (DatasetRole.IQR_RESULTS, 2, (
        "quartile", "25th", "35th", "75th", "median", "interquartile", "lower quartile",
        "upper quartile", "arm's length range", "arms length range")),
    (DatasetRole.SCREENING_RESULTS, 2, (
        "screening", "eliminated", "retained", "rejected", "reason for rejection",
        "search criteria", "passed", "step")),
    (DatasetRole.BENCHMARKING_DATA, 2, (
        "tp catalyst", "orbis", "bureau van dijk", "benchmark", "comparable set",
        "search strategy", "peer set")),
    (DatasetRole.FIXED_ASSETS, 2, (
        "fixed asset", "depreciation", "accumulated depreciation", "net book value",
        "tangible asset", "intangible asset", "historical cost")),
    (DatasetRole.RELATED_PARTY_TRANSACTIONS, 2, (
        "related party", "transaction", "amount (vnd)", "% of net sales", "type of relationship",
        "rpt", "intra-group", "intercompany")),
    (DatasetRole.INTEREST_EXPENSE, 2, (
        "interest", "credit institution", "principal", "maturity", "loan", "interest rate")),
    (DatasetRole.FINANCIAL_STATEMENTS, 2, (
        "net sales", "revenue", "cost of goods sold", "gross profit", "balance sheet",
        "total assets", "equity", "income statement", "profit before tax")),
    (DatasetRole.FINANCIAL_ANALYSIS, 2, (
        "ncp", "net cost plus", "operating margin", "return on assets", "profit level indicator",
        "ebit", "ratio", "margin")),
    (DatasetRole.SEGMENTED_DATA, 2, ("segment", "segmented", "allocation", "allocated")),
    (DatasetRole.RELATED_PARTIES_REGISTER, 2, (
        "related parties", "relationship", "country of incorporation", "ownership %", "parent")),
    (DatasetRole.CHECKLIST, 2, ("checklist", "prepared", "archived", "point of reference", "yes/no")),
    (DatasetRole.REFERENCE_LIST, 2, ("country list", "code", "description", "iso")),
]

_NUM_RE = re.compile(r"^[-+]?[\d.,]+$")


@dataclass
class ColumnRecordSchema:
    """One column of a sheet's detected record schema."""
    index: int
    letter: str
    header: str
    inferred_type: str
    unit_hint: Optional[str]
    non_empty: int
    sample: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "letter": self.letter, "header": self.header,
                "inferred_type": self.inferred_type, "unit_hint": self.unit_hint,
                "non_empty": self.non_empty, "sample": self.sample}


@dataclass
class SheetDatasetProfile:
    """Content-derived profile of a single worksheet."""
    sheet_name: str
    max_row: int
    max_column: int
    header_row_index: Optional[int]
    headers: List[str]
    record_schema: List[ColumnRecordSchema]
    record_count: int
    data_domain: DataDomain
    units_detected: List[str]
    formula_cell_count: int
    roles: List[DatasetRole]
    role_evidence: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "max_row": self.max_row,
            "max_column": self.max_column,
            "header_row_index": self.header_row_index,
            "headers": self.headers,
            "record_schema": [c.to_dict() for c in self.record_schema],
            "record_count": self.record_count,
            "data_domain": self.data_domain.value,
            "units_detected": self.units_detected,
            "formula_cell_count": self.formula_cell_count,
            "roles": [r.value for r in self.roles],
            "role_evidence": self.role_evidence,
        }


@dataclass
class WorkbookCapabilityProfile:
    """What a current-source workbook can and cannot supply."""
    document_name: str
    document_sha256: str
    sheet_count: int
    sheets: List[SheetDatasetProfile]

    def has_role(self, role: DatasetRole) -> bool:
        return any(role in s.roles for s in self.sheets)

    def sheets_with_role(self, role: DatasetRole) -> List[SheetDatasetProfile]:
        return [s for s in self.sheets if role in s.roles]

    def roles_present(self) -> List[DatasetRole]:
        seen: List[DatasetRole] = []
        for s in self.sheets:
            for r in s.roles:
                if r not in seen and r != DatasetRole.UNKNOWN:
                    seen.append(r)
        return seen

    def roles_absent(self) -> List[DatasetRole]:
        present = set(self.roles_present())
        return [r for r in DatasetRole if r not in present and r != DatasetRole.UNKNOWN]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "document_sha256": self.document_sha256,
            "sheet_count": self.sheet_count,
            "roles_present": [r.value for r in self.roles_present()],
            "roles_absent": [r.value for r in self.roles_absent()],
            "sheets": [s.to_dict() for s in self.sheets],
        }


class SourceCapabilityProfiler:
    """Profiles what datasets a workbook actually contains, from its content."""

    @classmethod
    def profile_workbook(cls, path: Path) -> WorkbookCapabilityProfile:
        wb_values = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
        wb_formulas = openpyxl.load_workbook(str(path), data_only=False, read_only=True)
        try:
            sheets = [
                cls._profile_sheet(wb_values[name], wb_formulas[name] if name in wb_formulas.sheetnames else None)
                for name in wb_values.sheetnames
            ]
        finally:
            wb_values.close()
            wb_formulas.close()

        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)

        return WorkbookCapabilityProfile(
            document_name=path.name,
            document_sha256=h.hexdigest(),
            sheet_count=len(sheets),
            sheets=sheets,
        )

    # ------------------------------------------------------------------

    @classmethod
    def _profile_sheet(cls, ws: Any, ws_formulas: Optional[Any]) -> SheetDatasetProfile:
        rows = cls._read_rows(ws)
        header_idx, headers = cls._detect_header(rows)
        data_rows = rows[header_idx + 1:] if header_idx is not None else rows

        schema = cls._record_schema(headers, data_rows)
        record_count = sum(1 for r in data_rows if any(cls._txt(v) for v in r))
        domain = cls._data_domain(data_rows)
        units = cls._units(headers, data_rows)
        formula_count = cls._formula_count(ws_formulas)
        roles, evidence = cls._detect_roles(headers, data_rows)

        return SheetDatasetProfile(
            sheet_name=ws.title,
            max_row=int(getattr(ws, "max_row", 0) or 0),
            max_column=int(getattr(ws, "max_column", 0) or 0),
            header_row_index=header_idx,
            headers=headers,
            record_schema=schema,
            record_count=record_count,
            data_domain=domain,
            units_detected=units,
            formula_cell_count=formula_count,
            roles=roles or [DatasetRole.UNKNOWN],
            role_evidence=evidence,
        )

    @staticmethod
    def _txt(v: Any) -> str:
        if v is None:
            return ""
        return re.sub(r"\s+", " ", str(v)).strip()

    @classmethod
    def _read_rows(cls, ws: Any) -> List[List[Any]]:
        out: List[List[Any]] = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= MAX_SCAN_ROWS:
                break
            out.append(list(row))
        return out

    @classmethod
    def _detect_header(cls, rows: List[List[Any]]) -> Tuple[Optional[int], List[str]]:
        """The header is the earliest row with the most distinct text cells."""
        best_idx, best_score, best_row = None, 0, []
        for i, row in enumerate(rows[:HEADER_SEARCH_DEPTH]):
            texts = [cls._txt(v) for v in row]
            labels = [t for t in texts if t and not _NUM_RE.match(t) and len(t) < 90]
            score = len(set(labels))
            if score > best_score:
                best_idx, best_score, best_row = i, score, texts
        if best_score < 2:
            return None, []
        return best_idx, best_row

    @classmethod
    def _record_schema(cls, headers: List[str], data_rows: List[List[Any]]) -> List[ColumnRecordSchema]:
        width = max([len(headers)] + [len(r) for r in data_rows[:50]] or [0])
        schema: List[ColumnRecordSchema] = []
        for c in range(width):
            col = [r[c] for r in data_rows if c < len(r)]
            vals = [v for v in col if cls._txt(v)]
            nums = sum(1 for v in vals if isinstance(v, (int, float)))
            inferred = "empty"
            if vals:
                if nums / len(vals) >= 0.7:
                    inferred = "numeric"
                elif sum(1 for v in vals if isinstance(v, str) and len(cls._txt(v)) > 60) / len(vals) >= 0.4:
                    inferred = "narrative"
                else:
                    inferred = "text"
            header = headers[c] if c < len(headers) else ""
            unit = None
            hl = header.lower()
            for token in ("vnd", "usd", "%", "million", "billion", "days", "times"):
                if token in hl:
                    unit = token
                    break
            schema.append(ColumnRecordSchema(
                index=c,
                letter=openpyxl.utils.get_column_letter(c + 1),
                header=header,
                inferred_type=inferred,
                unit_hint=unit,
                non_empty=len(vals),
                sample=cls._txt(vals[0])[:60] if vals else None,
            ))
        return schema

    @classmethod
    def _data_domain(cls, data_rows: List[List[Any]]) -> DataDomain:
        nums = texts = narr = 0
        for r in data_rows[:200]:
            for v in r:
                t = cls._txt(v)
                if not t:
                    continue
                if isinstance(v, (int, float)):
                    nums += 1
                elif len(t) > 80:
                    narr += 1
                else:
                    texts += 1
        total = nums + texts + narr
        if total == 0:
            return DataDomain.EMPTY
        if narr / total >= 0.3:
            return DataDomain.NARRATIVE
        if nums / total >= 0.6:
            return DataDomain.MONETARY
        if texts / total >= 0.7:
            return DataDomain.ENTITY
        return DataDomain.MIXED

    @classmethod
    def _units(cls, headers: List[str], data_rows: List[List[Any]]) -> List[str]:
        hay = " ".join(h.lower() for h in headers)
        for r in data_rows[:40]:
            hay += " " + " ".join(cls._txt(v).lower() for v in r)
        found = []
        for token in ("vnd", "usd", "%", "million", "billion", "eur", "jpy"):
            if token in hay:
                found.append(token)
        return found

    @staticmethod
    def _formula_count(ws_formulas: Optional[Any]) -> int:
        if ws_formulas is None:
            return 0
        count = 0
        for i, row in enumerate(ws_formulas.iter_rows(values_only=True)):
            if i >= MAX_SCAN_ROWS:
                break
            for v in row:
                if isinstance(v, str) and v.startswith("="):
                    count += 1
        return count

    @classmethod
    def _detect_roles(
        cls, headers: List[str], data_rows: List[List[Any]]
    ) -> Tuple[List[DatasetRole], Dict[str, List[str]]]:
        """Assigns roles from observed content only. Sheet name is never consulted."""
        hay = " | ".join(h.lower() for h in headers)
        # Label evidence often sits in a code column followed by a name column,
        # so read the leading label band rather than only the first cell.
        for r in data_rows[:80]:
            for c in range(min(3, len(r))):
                t = cls._txt(r[c]).lower()
                if t and not _NUM_RE.match(t) and len(t) < 90:
                    hay += " || " + t
        roles: List[Tuple[int, DatasetRole]] = []
        evidence: Dict[str, List[str]] = {}
        for role, threshold, tokens in _ROLE_SIGNALS:
            hits = [t for t in tokens if t in hay]
            if len(hits) >= threshold:
                roles.append((len(hits), role))
                evidence[role.value] = hits
        roles.sort(key=lambda t: (-t[0], t[1].value))
        return [r for _, r in roles], evidence

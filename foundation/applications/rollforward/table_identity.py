"""
Multi-Factor Table Identity & Cross-Document Correspondence (Phase C2)
======================================================================
Location: foundation/applications/rollforward/table_identity.py

Replaces positional table identity in Roll-Forward planning.

Phase D3.1 proved that correlating the FY2023 Local File, the Master Template
and the FY2024 output by `tables[i]` produces phantom deltas: those documents
hold 22, 16 and 19 tables, so index *i* denotes a different table in each.

This module establishes the replacement invariant:

    A table's identity is its SECTION CONTEXT, HEADING CONTEXT, HEADER
    SIGNATURE, COLUMN SCHEMA, ROW SCHEMA, MERGE TOPOLOGY, NEIGHBOURING
    ELEMENTS and SEMANTIC LABELS -- never its ordinal.

`ordinal` is retained on every signature purely as a display/order attribute
and as an intra-document locator. It is never an input to correspondence:
`TableCorrespondenceResolver` cannot see it.

This module performs no mutation and reads no Ground Truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table

# Heading styles that open a section context.
_HEADING_RE = re.compile(r"^(heading\s*\d+|title|subtitle)$", re.IGNORECASE)
_NUM_RE = re.compile(r"^[\s(]*[-+]?[\d.,]+\s*%?[\s)]*$")
_MONEY_RE = re.compile(r"^[\s(]*[-+]?[\d][\d.,]*\s*(vnd|usd|dong|đ)?[\s)]*$", re.IGNORECASE)
_PLACEHOLDER_RE = re.compile(r"^(x{2,}|y{2,}|z{2,}|n/a|-{1,3}|…|\.{3}|company\s*\d+|…)$", re.IGNORECASE)


class CorrespondenceConfidence(str, Enum):
    """How strongly two tables in different documents are the same table."""
    EXACT = "EXACT"                # identical header signature and column schema
    STRONG = "STRONG"              # same semantic labels + compatible column roles
    WEAK = "WEAK"                  # partial header overlap only; needs human confirmation
    UNCORRELATED = "UNCORRELATED"  # no counterpart could be established


class SemanticLabel(str, Enum):
    """Content-derived label for a Transfer Pricing Local File table."""
    ARMS_LENGTH_RANGE = "ARMS_LENGTH_RANGE"
    COMPARABLE_COMPANIES = "COMPARABLE_COMPANIES"
    SCREENING_STRATEGY = "SCREENING_STRATEGY"
    SCREENING_REJECTION = "SCREENING_REJECTION"
    SEARCH_STEP_MATRIX = "SEARCH_STEP_MATRIX"
    INDUSTRY_CODE_LIST = "INDUSTRY_CODE_LIST"
    OWNERSHIP_CODE_LIST = "OWNERSHIP_CODE_LIST"
    RELATED_PARTY_TRANSACTIONS = "RELATED_PARTY_TRANSACTIONS"
    FINANCIAL_INDICATORS = "FINANCIAL_INDICATORS"
    FUNCTIONAL_ANALYSIS = "FUNCTIONAL_ANALYSIS"
    PLI_FORMULA = "PLI_FORMULA"
    INTEREST_SCHEDULE = "INTEREST_SCHEDULE"
    DOCUMENT_CHECKLIST = "DOCUMENT_CHECKLIST"
    COVER_BLOCK = "COVER_BLOCK"
    UNKNOWN = "UNKNOWN"


# Content signals for each semantic label. Matched against the header row and
# the first-column labels -- never against the table's position.
_LABEL_SIGNALS: List[Tuple[SemanticLabel, Sequence[str], int]] = [
    (SemanticLabel.ARMS_LENGTH_RANGE, ("percentile", "median", "interquartile", "pli in fy"), 1),
    (SemanticLabel.PLI_FORMULA, ("ncp", "roa", "om ", "= ebit", "ebit"), 2),
    (SemanticLabel.SCREENING_STRATEGY, ("database used", "tp catalyst", "status screen",
                                        "geographic screen", "keyword screen", "independence screen",
                                        "quantitative screens", "qualitative screens"), 2),
    (SemanticLabel.SEARCH_STEP_MATRIX, ("step", "search criteria", "passed", "search equation"), 3),
    (SemanticLabel.SCREENING_REJECTION, ("screening criteria", "eliminated", "retained",
                                         "reason for rejection", "reasons for rejection"), 2),
    (SemanticLabel.COMPARABLE_COMPANIES, ("company", "ticker", "tax code", "vn sic code",
                                          "business description", "province", "country"), 3),
    (SemanticLabel.INDUSTRY_CODE_LIST, ("sic code", "naics code", "code", "description"), 2),
    (SemanticLabel.OWNERSHIP_CODE_LIST, ("shareholder", "ownership"), 1),
    (SemanticLabel.RELATED_PARTY_TRANSACTIONS, ("transaction", "related party", "amount (vnd)",
                                                "% of net sales", "type of relationship"), 2),
    (SemanticLabel.FINANCIAL_INDICATORS, ("net sales", "unit: vnd", "index", "cost of goods sold",
                                          "gross profit", "operating profit"), 2),
    (SemanticLabel.FUNCTIONAL_ANALYSIS, ("functions/assets/risks", "functions", "assets", "risks"), 1),
    (SemanticLabel.INTEREST_SCHEDULE, ("credit institutions", "annual interest rate", "principal",
                                       "maturity date", "financing date"), 2),
    (SemanticLabel.DOCUMENT_CHECKLIST, ("documents", "prepared and archived", "point of reference",
                                        "details"), 2),
    (SemanticLabel.COVER_BLOCK, ("this report contains", "co., ltd", "limited liability"), 1),
]


class ColumnKind(str, Enum):
    """Coarse, content-derived kind of a table column."""
    ORDINAL = "ORDINAL"
    TEXT = "TEXT"
    NUMERIC = "NUMERIC"
    MONETARY = "MONETARY"
    PERCENTAGE = "PERCENTAGE"
    CODE = "CODE"
    EMPTY = "EMPTY"
    PLACEHOLDER = "PLACEHOLDER"
    MIXED = "MIXED"


@dataclass(frozen=True)
class ColumnSchema:
    """Header text plus the content kind observed down a column."""
    index: int
    header: str
    kind: ColumnKind
    non_empty_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {"index": self.index, "header": self.header, "kind": self.kind.value,
                "non_empty_ratio": round(self.non_empty_ratio, 3)}


@dataclass
class TableIdentitySignature:
    """Everything that identifies a table WITHOUT reference to its position.

    `ordinal` is present for display and for addressing the table inside its
    own document. `identity_key` and every comparison method deliberately
    exclude it.
    """
    document_id: str
    ordinal: int                       # DISPLAY / INTRA-DOCUMENT LOCATOR ONLY
    section_path: Tuple[str, ...]
    nearest_heading: str
    caption_before: str
    caption_after: str
    header_cells: Tuple[str, ...]
    header_signature: str
    column_schemas: Tuple[ColumnSchema, ...]
    column_count: int
    row_count: int
    row_label_signature: str
    merge_signature: str
    semantic_labels: Tuple[SemanticLabel, ...]
    table_hash: Optional[str] = None
    placeholder_row_count: int = 0

    @property
    def identity_key(self) -> str:
        """Position-free identity digest."""
        h = hashlib.sha256()
        h.update("|".join(self.header_cells).lower().encode("utf-8"))
        h.update(b"::")
        h.update("|".join(c.kind.value for c in self.column_schemas).encode("utf-8"))
        h.update(b"::")
        h.update("|".join(sorted(l.value for l in self.semantic_labels)).encode("utf-8"))
        return h.hexdigest()[:16]

    @property
    def primary_label(self) -> SemanticLabel:
        return self.semantic_labels[0] if self.semantic_labels else SemanticLabel.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "ordinal_display_only": self.ordinal,
            "identity_key": self.identity_key,
            "section_path": list(self.section_path),
            "nearest_heading": self.nearest_heading,
            "caption_before": self.caption_before,
            "caption_after": self.caption_after,
            "header_cells": list(self.header_cells),
            "header_signature": self.header_signature,
            "column_schemas": [c.to_dict() for c in self.column_schemas],
            "column_count": self.column_count,
            "row_count": self.row_count,
            "row_label_signature": self.row_label_signature,
            "merge_signature": self.merge_signature,
            "semantic_labels": [l.value for l in self.semantic_labels],
            "table_hash": self.table_hash,
            "placeholder_row_count": self.placeholder_row_count,
        }


@dataclass
class TableCorrespondence:
    """A resolved (or explicitly unresolved) cross-document table pairing."""
    left: TableIdentitySignature
    right: Optional[TableIdentitySignature]
    confidence: CorrespondenceConfidence
    score: float
    matched_factors: List[str] = field(default_factory=list)
    divergent_factors: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "left_document": self.left.document_id,
            "left_ordinal_display_only": self.left.ordinal,
            "left_identity_key": self.left.identity_key,
            "left_labels": [l.value for l in self.left.semantic_labels],
            "right_document": self.right.document_id if self.right else None,
            "right_ordinal_display_only": self.right.ordinal if self.right else None,
            "right_identity_key": self.right.identity_key if self.right else None,
            "right_labels": [l.value for l in self.right.semantic_labels] if self.right else [],
            "confidence": self.confidence.value,
            "score": round(self.score, 4),
            "matched_factors": list(self.matched_factors),
            "divergent_factors": list(self.divergent_factors),
            "rationale": self.rationale,
        }


# ============================================================================
# PROFILER
# ============================================================================

def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace(" ", " ")).strip()


def _cell_kind(values: Sequence[str]) -> ColumnKind:
    """Classifies a column by the content actually observed in its data cells."""
    vals = [v for v in (_norm(v) for v in values) if v]
    if not vals:
        return ColumnKind.EMPTY
    if all(_PLACEHOLDER_RE.match(v) for v in vals):
        return ColumnKind.PLACEHOLDER
    pct = sum(1 for v in vals if v.endswith("%"))
    num = sum(1 for v in vals if _NUM_RE.match(v))
    money = sum(1 for v in vals if _MONEY_RE.match(v) and len(v.replace(",", "")) >= 7)
    ordinal = sum(1 for v in vals if v.isdigit() and len(v) <= 3)
    n = len(vals)
    if pct / n >= 0.6:
        return ColumnKind.PERCENTAGE
    if money / n >= 0.6:
        return ColumnKind.MONETARY
    if ordinal / n >= 0.8:
        return ColumnKind.ORDINAL
    if num / n >= 0.6:
        return ColumnKind.NUMERIC
    if sum(1 for v in vals if re.fullmatch(r"[A-Z0-9\-./]{2,14}", v)) / n >= 0.7:
        return ColumnKind.CODE
    if num or pct:
        return ColumnKind.MIXED
    return ColumnKind.TEXT


def _detect_labels(header_cells: Sequence[str], row_labels: Sequence[str]) -> Tuple[SemanticLabel, ...]:
    """Content-derived semantic labels. Never consults position."""
    hay = " | ".join(_norm(h).lower() for h in header_cells)
    hay += " || " + " | ".join(_norm(r).lower() for r in row_labels[:24])
    found: List[Tuple[int, SemanticLabel]] = []
    for label, signals, threshold in _LABEL_SIGNALS:
        hits = sum(1 for s in signals if s in hay)
        if hits >= threshold:
            found.append((hits, label))
    found.sort(key=lambda t: (-t[0], t[1].value))
    return tuple(l for _, l in found) or (SemanticLabel.UNKNOWN,)


class TableIdentityProfiler:
    """Builds position-free identity signatures for every table in a document."""

    @classmethod
    def profile_document(cls, doc_path: Path, document_id: Optional[str] = None) -> List[TableIdentitySignature]:
        doc = Document(str(doc_path))
        doc_id = document_id or doc_path.name
        context = cls._body_context(doc)
        sigs: List[TableIdentitySignature] = []
        for ordinal, table in enumerate(doc.tables):
            ctx = context.get(ordinal, {})
            sigs.append(cls.profile_table(
                table=table, ordinal=ordinal, document_id=doc_id,
                section_path=ctx.get("section_path", ()),
                caption_before=ctx.get("before", ""),
                caption_after=ctx.get("after", ""),
            ))
        return sigs

    @classmethod
    def profile_table(
        cls,
        table: Table,
        ordinal: int,
        document_id: str,
        section_path: Tuple[str, ...] = (),
        caption_before: str = "",
        caption_after: str = "",
    ) -> TableIdentitySignature:
        rows = table.rows
        header_cells = tuple(_norm(c.text) for c in rows[0].cells) if rows else ()
        col_count = len(table.columns)

        columns: List[ColumnSchema] = []
        for c_idx in range(col_count):
            col_vals: List[str] = []
            for r in rows[1:]:
                cells = r.cells
                if c_idx < len(cells):
                    col_vals.append(cells[c_idx].text)
            non_empty = sum(1 for v in col_vals if _norm(v))
            columns.append(ColumnSchema(
                index=c_idx,
                header=header_cells[c_idx] if c_idx < len(header_cells) else "",
                kind=_cell_kind(col_vals),
                non_empty_ratio=(non_empty / len(col_vals)) if col_vals else 0.0,
            ))

        row_labels = [_norm(r.cells[0].text) if r.cells else "" for r in rows[1:]]
        placeholder_rows = sum(1 for v in row_labels if _PLACEHOLDER_RE.match(v)) + \
            sum(1 for r in rows[1:] if all(not _norm(c.text) for c in r.cells))

        merge_h = hashlib.sha256()
        for r_idx, r in enumerate(rows):
            for c_idx, tc in enumerate(r._tr.findall(qn("w:tc"))):
                tcPr = tc.find(qn("w:tcPr"))
                gs = tcPr.find(qn("w:gridSpan")) if tcPr is not None else None
                vm = tcPr.find(qn("w:vMerge")) if tcPr is not None else None
                merge_h.update(
                    f"{r_idx}:{c_idx}:{gs.get(qn('w:val')) if gs is not None else 1}:"
                    f"{(vm.get(qn('w:val')) or 'continue') if vm is not None else 'none'}|".encode("utf-8")
                )

        return TableIdentitySignature(
            document_id=document_id,
            ordinal=ordinal,
            section_path=tuple(section_path),
            nearest_heading=section_path[-1] if section_path else "",
            caption_before=caption_before,
            caption_after=caption_after,
            header_cells=header_cells,
            header_signature=hashlib.sha256(
                "|".join(h.lower() for h in header_cells).encode("utf-8")
            ).hexdigest()[:16],
            column_schemas=tuple(columns),
            column_count=col_count,
            row_count=len(rows),
            row_label_signature=hashlib.sha256(
                "|".join(v.lower() for v in row_labels).encode("utf-8")
            ).hexdigest()[:16],
            merge_signature=merge_h.hexdigest()[:16],
            semantic_labels=_detect_labels(header_cells, row_labels),
            placeholder_row_count=placeholder_rows,
        )

    @staticmethod
    def _body_context(doc: Document) -> Dict[int, Dict[str, Any]]:
        """Walks the body once, recording each table's heading chain and neighbours."""
        from docx.text.paragraph import Paragraph

        out: Dict[int, Dict[str, Any]] = {}
        heading_stack: List[Tuple[int, str]] = []
        last_para = ""
        t_ordinal = 0
        pending: List[int] = []

        for child in doc.element.body:
            tag = child.tag.split("}")[-1]
            if tag == "p":
                p = Paragraph(child, doc)
                text = _norm(p.text)
                style = p.style.name if p.style else ""
                m = _HEADING_RE.match(style.strip())
                if m and text:
                    lvl_digits = re.findall(r"\d+", style)
                    level = int(lvl_digits[0]) if lvl_digits else 0
                    while heading_stack and heading_stack[-1][0] >= level:
                        heading_stack.pop()
                    heading_stack.append((level, text))
                if text:
                    for t_idx in pending:
                        out[t_idx]["after"] = text
                    pending = []
                    last_para = text
            elif tag == "tbl":
                out[t_ordinal] = {
                    "section_path": tuple(h for _, h in heading_stack),
                    "before": last_para,
                    "after": "",
                }
                pending.append(t_ordinal)
                t_ordinal += 1
        return out


# ============================================================================
# CORRESPONDENCE RESOLVER
# ============================================================================

class TableCorrespondenceResolver:
    """Resolves cross-document table correspondence WITHOUT using position.

    The scoring function receives only position-free factors. `ordinal` is
    never read here; `assert_no_positional_input` proves it.
    """

    WEIGHTS = {
        "header_signature": 0.30,
        "semantic_label": 0.24,
        "header_token_overlap": 0.22,
        "column_schema_alignment": 0.14,
        "section_context": 0.06,
        "merge_topology": 0.04,
    }
    # Column kinds that carry no evidence either way: a template's unfilled
    # placeholder column cannot agree or disagree with a populated one.
    NEUTRAL_KINDS = {ColumnKind.EMPTY, ColumnKind.PLACEHOLDER}
    STRONG_THRESHOLD = 0.62
    WEAK_THRESHOLD = 0.34

    @classmethod
    def score(cls, a: TableIdentitySignature, b: TableIdentitySignature) -> Tuple[float, List[str], List[str]]:
        matched: List[str] = []
        divergent: List[str] = []
        total = 0.0

        if a.header_signature == b.header_signature and a.header_cells:
            total += cls.WEIGHTS["header_signature"]
            matched.append("header_signature")
        else:
            divergent.append("header_signature")

        shared_labels = set(a.semantic_labels) & set(b.semantic_labels) - {SemanticLabel.UNKNOWN}
        if shared_labels:
            frac = len(shared_labels) / max(1, len(set(a.semantic_labels) | set(b.semantic_labels)
                                                - {SemanticLabel.UNKNOWN}))
            total += cls.WEIGHTS["semantic_label"] * frac
            matched.append(f"semantic_label({','.join(sorted(l.value for l in shared_labels))})")
        else:
            divergent.append("semantic_label")

        align_score, aligned_pairs = cls._column_alignment_score(a, b)
        if aligned_pairs:
            total += cls.WEIGHTS["column_schema_alignment"] * align_score
            (matched if align_score >= 0.6 else divergent).append("column_schema_alignment")

        a_tok = {t for h in a.header_cells for t in re.findall(r"[a-z]{3,}", h.lower())}
        b_tok = {t for h in b.header_cells for t in re.findall(r"[a-z]{3,}", h.lower())}
        if a_tok and b_tok:
            jac = len(a_tok & b_tok) / len(a_tok | b_tok)
            total += cls.WEIGHTS["header_token_overlap"] * jac
            (matched if jac >= 0.4 else divergent).append("header_token_overlap")

        a_ctx = " ".join(a.section_path + (a.caption_before,)).lower()
        b_ctx = " ".join(b.section_path + (b.caption_before,)).lower()
        a_ctok = set(re.findall(r"[a-z]{4,}", a_ctx))
        b_ctok = set(re.findall(r"[a-z]{4,}", b_ctx))
        if a_ctok and b_ctok:
            jac = len(a_ctok & b_ctok) / len(a_ctok | b_ctok)
            total += cls.WEIGHTS["section_context"] * jac
            if jac >= 0.25:
                matched.append("section_context")

        if a.merge_signature == b.merge_signature:
            total += cls.WEIGHTS["merge_topology"]
            matched.append("merge_topology")

        return total, matched, divergent

    @classmethod
    def _column_alignment_score(
        cls, a: TableIdentitySignature, b: TableIdentitySignature
    ) -> Tuple[float, int]:
        """Aligns columns by header wording, then compares their content kinds.

        Alignment is by header text, never by column position, and neutral
        (empty / placeholder) columns are excluded from the kind comparison
        rather than counted as disagreement.
        """
        def toks(h: str) -> Set[str]:
            return set(re.findall(r"[a-z]{3,}", h.lower()))

        remaining = list(b.column_schemas)
        aligned: List[Tuple[ColumnSchema, ColumnSchema]] = []
        for ca in a.column_schemas:
            ta = toks(ca.header)
            best, best_j = None, 0.0
            for cb in remaining:
                tb = toks(cb.header)
                if not ta or not tb:
                    continue
                j = len(ta & tb) / len(ta | tb)
                if j > best_j:
                    best, best_j = cb, j
            if best is not None and best_j >= 0.3:
                aligned.append((ca, best))
                remaining.remove(best)

        if not aligned:
            return 0.0, 0

        comparable = [(x, y) for x, y in aligned
                      if x.kind not in cls.NEUTRAL_KINDS and y.kind not in cls.NEUTRAL_KINDS]
        kind_agreement = (
            sum(1 for x, y in comparable if x.kind == y.kind) / len(comparable)
            if comparable else 1.0
        )
        coverage = len(aligned) / max(len(a.column_schemas), len(b.column_schemas), 1)
        return kind_agreement * coverage, len(aligned)

    @classmethod
    def correspond(
        cls,
        left: Sequence[TableIdentitySignature],
        right: Sequence[TableIdentitySignature],
    ) -> List[TableCorrespondence]:
        """Best position-free match for every left table; UNCORRELATED when none."""
        out: List[TableCorrespondence] = []
        for a in left:
            best: Optional[TableIdentitySignature] = None
            best_score = 0.0
            best_matched: List[str] = []
            best_divergent: List[str] = []
            for b in right:
                s, m, d = cls.score(a, b)
                if s > best_score:
                    best, best_score, best_matched, best_divergent = b, s, m, d

            if best is None or best_score < cls.WEAK_THRESHOLD:
                out.append(TableCorrespondence(
                    left=a, right=None, confidence=CorrespondenceConfidence.UNCORRELATED,
                    score=best_score, divergent_factors=best_divergent or ["no_candidate"],
                    rationale=("No table in the counterpart document reaches the weak-correspondence "
                               f"threshold ({cls.WEAK_THRESHOLD}). Best score {best_score:.3f}."),
                ))
                continue

            if best.header_signature == a.header_signature and a.header_cells:
                conf = CorrespondenceConfidence.EXACT
            elif best_score >= cls.STRONG_THRESHOLD:
                conf = CorrespondenceConfidence.STRONG
            else:
                conf = CorrespondenceConfidence.WEAK

            out.append(TableCorrespondence(
                left=a, right=best, confidence=conf, score=best_score,
                matched_factors=best_matched, divergent_factors=best_divergent,
                rationale=(f"Matched on {', '.join(best_matched) or 'partial signals'} "
                           f"(score {best_score:.3f}); ordinal was not an input."),
            ))
        return out

    @classmethod
    def assert_no_positional_input(cls) -> bool:
        """Proves the scoring function cannot read `ordinal`.

        Two signatures that differ only in `ordinal` must score identically
        against any third signature.
        """
        import dataclasses

        probe = TableIdentitySignature(
            document_id="probe", ordinal=0, section_path=("S",), nearest_heading="S",
            caption_before="", caption_after="", header_cells=("A", "B"),
            header_signature="hs", column_schemas=(), column_count=2, row_count=2,
            row_label_signature="rl", merge_signature="mg",
            semantic_labels=(SemanticLabel.UNKNOWN,),
        )
        shifted = dataclasses.replace(probe, ordinal=999)
        other = dataclasses.replace(probe, document_id="other", ordinal=7)
        return cls.score(probe, other)[0] == cls.score(shifted, other)[0]

"""
Mutation Precondition Gate & Real Postcondition Hashing (Phase C2 / D3.2)
=========================================================================
Location: foundation/applications/rollforward/mutation_precondition.py

Two Phase D3.1 findings are closed here.

P0-3 — semantic placement. D1/D3 wrote P&L line items into an arm's-length
range table, appended rows below a full-width footer, and put a percentage in
a "Business description" column, and every structural gate passed. Structural
validity was treated as semantic validity. `MutationPreconditionValidator`
runs BEFORE D1 and BLOCKS a plan whose rows do not belong where they are aimed.

P0-6 — `expected_postcondition_hash = "dummy"`. A placeholder can never equal
a live fingerprint, so D1's idempotence NOOP could never fire on a real
fixture. `PostconditionHasher` computes a deterministic semantic hash of a
table, and — crucially — can PROJECT that hash for a plan that has not run
yet, so a real expected postcondition can be recorded before execution.

This module blocks and hashes. It never mutates a document.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table, _Row

from applications.rollforward.semantic_binding import (
    RowSemantics,
    TargetRegionSchema,
)
from applications.rollforward.table_identity import TableIdentityProfiler


class PreconditionViolationCode(str, Enum):
    """Why a mutation plan may not proceed to D1."""
    TABLE_IDENTITY_MISMATCH = "TABLE_IDENTITY_MISMATCH"
    TABLE_NOT_FOUND = "TABLE_NOT_FOUND"
    COLUMN_COUNT_MISMATCH = "COLUMN_COUNT_MISMATCH"
    COLUMN_DOMAIN_VIOLATION = "COLUMN_DOMAIN_VIOLATION"
    ROW_SEMANTICS_MISMATCH = "ROW_SEMANTICS_MISMATCH"
    INSERTION_BELOW_FOOTER = "INSERTION_BELOW_FOOTER"
    INSERTION_OUTSIDE_DATA_REGION = "INSERTION_OUTSIDE_DATA_REGION"
    PLACEHOLDER_ROWS_NOT_CONSUMED = "PLACEHOLDER_ROWS_NOT_CONSUMED"
    MERGE_TOPOLOGY_UNSAFE = "MERGE_TOPOLOGY_UNSAFE"
    ROW_SCHEMA_MISMATCH = "ROW_SCHEMA_MISMATCH"
    DUMMY_POSTCONDITION_HASH = "DUMMY_POSTCONDITION_HASH"


# Values that have been used as postcondition placeholders and must never
# be accepted as a real expected-postcondition hash.
FORBIDDEN_POSTCONDITION_VALUES = {"", "dummy", "post", "post-dummy", "none", "null", "todo", "tbd"}


@dataclass
class PreconditionViolation:
    code: PreconditionViolationCode
    region_id: str
    table_ordinal: int
    detail: str
    location: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code.value, "region_id": self.region_id,
                "table_ordinal_display_only": self.table_ordinal,
                "detail": self.detail, "location": self.location}


@dataclass
class TableAnatomy:
    """Header band, data region, placeholder rows and footer band of a table."""
    ordinal: int
    row_count: int
    column_count: int
    header_row_count: int
    footer_row_idxs: Tuple[int, ...]
    placeholder_row_idxs: Tuple[int, ...]
    ellipsis_row_idxs: Tuple[int, ...]

    @property
    def data_region(self) -> Tuple[int, int]:
        start = self.header_row_count
        end = (min(self.footer_row_idxs) - 1) if self.footer_row_idxs else self.row_count - 1
        return start, end

    @property
    def append_position(self) -> int:
        """The last row index a new row may legitimately be inserted after."""
        return self.data_region[1]

    def to_dict(self) -> Dict[str, Any]:
        return {"ordinal_display_only": self.ordinal, "row_count": self.row_count,
                "column_count": self.column_count, "header_row_count": self.header_row_count,
                "footer_row_idxs": list(self.footer_row_idxs),
                "placeholder_row_idxs": list(self.placeholder_row_idxs),
                "ellipsis_row_idxs": list(self.ellipsis_row_idxs),
                "data_region": list(self.data_region),
                "append_position": self.append_position}


_PLACEHOLDER_CELL = re.compile(
    r"^(x{2,}%?|y{2,}|z{2,}|company\s*\d+|…|\.{3}|-{1,3}|n/?a)$", re.IGNORECASE)


class TableAnatomyProfiler:
    """Derives header / data / placeholder / footer bands from a live table."""

    @classmethod
    def profile(cls, table: Table, ordinal: int) -> TableAnatomy:
        rows = table.rows
        n = len(rows)
        col_count = len(table.columns)

        footer: List[int] = []
        placeholders: List[int] = []
        ellipsis: List[int] = []

        for r_idx in range(1, n):
            texts = [re.sub(r"\s+", " ", c.text).strip() for c in rows[r_idx].cells]
            non_empty = [t for t in texts if t]
            # A full-width spanned band surfaces as every cell repeating one string.
            if len(texts) > 1 and non_empty and len(set(texts)) == 1:
                footer.append(r_idx)
                continue
            if non_empty and all(_PLACEHOLDER_CELL.match(t) for t in non_empty):
                placeholders.append(r_idx)
                if any(t in ("…", "...") for t in non_empty):
                    ellipsis.append(r_idx)
                continue
            if not non_empty:
                placeholders.append(r_idx)

        # Only a TRAILING run of spanned bands is a footer; an interior one is data.
        trailing_footer: List[int] = []
        expected = n - 1
        for r_idx in sorted(footer, reverse=True):
            if r_idx == expected:
                trailing_footer.append(r_idx)
                expected -= 1
        trailing_footer.sort()

        return TableAnatomy(
            ordinal=ordinal,
            row_count=n,
            column_count=col_count,
            header_row_count=1,
            footer_row_idxs=tuple(trailing_footer),
            placeholder_row_idxs=tuple(placeholders),
            ellipsis_row_idxs=tuple(ellipsis),
        )


@dataclass
class PreconditionReport:
    """Outcome of the pre-D1 gate."""
    is_executable: bool
    violations: List[PreconditionViolation] = field(default_factory=list)
    anatomies: Dict[int, TableAnatomy] = field(default_factory=dict)
    checked_regions: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_executable": self.is_executable,
            "checked_regions": self.checked_regions,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "anatomies": {str(k): v.to_dict() for k, v in self.anatomies.items()},
            "passed_checks": self.passed_checks,
        }


class MutationPreconditionValidator:
    """Blocks a mutation plan that is structurally legal but semantically wrong."""

    @classmethod
    def validate(
        cls,
        template_path: Path,
        table_mutations: Sequence[Any],
        schemas: Dict[str, TargetRegionSchema],
        require_real_postcondition: bool = True,
    ) -> PreconditionReport:
        """Validates every TableMutationSpec against its declared target schema.

        `table_mutations` are D1 `TableMutationSpec` objects; they are read,
        never modified.
        """
        report = PreconditionReport(is_executable=True)
        doc = Document(str(template_path))
        signatures = {s.ordinal: s for s in TableIdentityProfiler.profile_document(template_path)}

        for spec in table_mutations:
            region_id = spec.target_region_id
            ordinal = spec.table_index
            report.checked_regions.append(region_id)
            schema = schemas.get(region_id)

            if ordinal >= len(doc.tables):
                cls._violate(report, PreconditionViolationCode.TABLE_NOT_FOUND, region_id, ordinal,
                             f"Template has {len(doc.tables)} tables; plan targets ordinal {ordinal}.")
                continue

            table = doc.tables[ordinal]
            anatomy = TableAnatomyProfiler.profile(table, ordinal)
            report.anatomies[ordinal] = anatomy

            # --- real postcondition hash (P0-6) --------------------------
            if require_real_postcondition:
                value = (getattr(spec, "expected_postcondition_hash", "") or "").strip().lower()
                if value in FORBIDDEN_POSTCONDITION_VALUES:
                    cls._violate(
                        report, PreconditionViolationCode.DUMMY_POSTCONDITION_HASH, region_id, ordinal,
                        f"expected_postcondition_hash is the placeholder "
                        f"'{getattr(spec, 'expected_postcondition_hash', '')}'. Idempotence cannot be "
                        f"proven against a placeholder; compute it with PostconditionHasher.project().")
                else:
                    report.passed_checks.append(f"{region_id}: real expected_postcondition_hash present")

            # --- table identity (P0-1) ------------------------------------
            sig = signatures.get(ordinal)
            if schema is not None and sig is not None:
                if schema.table_identity_key != sig.identity_key:
                    cls._violate(
                        report, PreconditionViolationCode.TABLE_IDENTITY_MISMATCH, region_id, ordinal,
                        f"Plan targets a table whose position-free identity key is "
                        f"{sig.identity_key}, but region {region_id} declares "
                        f"{schema.table_identity_key}. The table at this ordinal is not the "
                        f"table the region describes.")
                    continue
                report.passed_checks.append(f"{region_id}: table identity key matches ({sig.identity_key})")

            if schema is None:
                cls._violate(report, PreconditionViolationCode.ROW_SCHEMA_MISMATCH, region_id, ordinal,
                             f"No TargetRegionSchema declared for region {region_id}; a mutation "
                             f"may not proceed without declared target semantics.")
                continue

            # --- column count ---------------------------------------------
            if len(schema.columns) != anatomy.column_count:
                cls._violate(report, PreconditionViolationCode.COLUMN_COUNT_MISMATCH, region_id, ordinal,
                             f"Schema declares {len(schema.columns)} columns; table has "
                             f"{anatomy.column_count}.")

            # --- row semantics --------------------------------------------
            if schema.row_semantics in (RowSemantics.STATISTIC, RowSemantics.KEY_VALUE) and spec.row_mutations:
                cls._violate(
                    report, PreconditionViolationCode.ROW_SEMANTICS_MISMATCH, region_id, ordinal,
                    f"Region row semantics are {schema.row_semantics.value}: each row is a fixed, "
                    f"uniquely-labelled entry, not a repeatable record. Appending "
                    f"{len(spec.row_mutations)} rows is not a valid roll-forward of this table; "
                    f"it requires cell update / placeholder activation instead.")

            # --- insertion location vs footer & data region ---------------
            data_start, data_end = anatomy.data_region
            for row_mut in spec.row_mutations:
                r_idx = row_mut.row_idx
                if anatomy.footer_row_idxs and r_idx > min(anatomy.footer_row_idxs):
                    cls._violate(
                        report, PreconditionViolationCode.INSERTION_BELOW_FOOTER, region_id, ordinal,
                        f"Row {r_idx} would be written below the table's footer band "
                        f"(rows {list(anatomy.footer_row_idxs)}). New records must land inside the "
                        f"data region [{data_start}, {data_end}].",
                        location=f"table {ordinal} row {r_idx}")
                elif r_idx < data_start:
                    cls._violate(
                        report, PreconditionViolationCode.INSERTION_OUTSIDE_DATA_REGION, region_id, ordinal,
                        f"Row {r_idx} falls inside the header band (rows 0..{data_start - 1}).",
                        location=f"table {ordinal} row {r_idx}")

                # --- column domain compatibility (P0-3) -------------------
                for cell in row_mut.cells:
                    ok, why = schema_accepts(schema, cell.col_idx, cell.value)
                    if not ok:
                        cls._violate(
                            report, PreconditionViolationCode.COLUMN_DOMAIN_VIOLATION, region_id, ordinal,
                            why, location=f"table {ordinal} row {r_idx} col {cell.col_idx}")

            # --- unconsumed placeholder rows -------------------------------
            live_placeholders = [p for p in anatomy.placeholder_row_idxs
                                 if p not in anatomy.footer_row_idxs]
            if live_placeholders and spec.row_mutations:
                lowest_new = min(rm.row_idx for rm in spec.row_mutations)
                if lowest_new > max(live_placeholders):
                    cls._violate(
                        report, PreconditionViolationCode.PLACEHOLDER_ROWS_NOT_CONSUMED, region_id, ordinal,
                        f"Rows {live_placeholders} are unfilled template placeholders and every new "
                        f"row is appended after them (first new row {lowest_new}). The published "
                        f"table would carry placeholders and real records side by side.")

        report.is_executable = not report.violations
        return report

    @staticmethod
    def _violate(report: PreconditionReport, code: PreconditionViolationCode,
                 region_id: str, ordinal: int, detail: str, location: str = "") -> None:
        report.violations.append(PreconditionViolation(
            code=code, region_id=region_id, table_ordinal=ordinal, detail=detail, location=location))
        report.is_executable = False


def schema_accepts(schema: TargetRegionSchema, col_idx: int, value: Any) -> Tuple[bool, str]:
    """Thin wrapper so callers need not import the binding module directly."""
    from applications.rollforward.semantic_binding import SemanticBindingValidator
    return SemanticBindingValidator.validate_value_against_column(schema, col_idx, value)


# ============================================================================
# REAL POSTCONDITION HASHING (P0-6)
# ============================================================================

@dataclass(frozen=True)
class CellState:
    """Semantic state of a single cell for hashing purposes."""
    text: str
    grid_span: int
    v_merge: str
    style_signature: str


class PostconditionHasher:
    """Deterministic semantic postcondition hashes, computable before execution.

    `from_table` hashes a live table. `project` hashes the table a plan WOULD
    produce, without touching the document, so a real expected postcondition
    can be recorded at planning time instead of the placeholder that
    Phase D3.1 found.

    Both paths feed the same `_digest`, so a projected hash and the hash of the
    executed result are directly comparable.
    """

    ALGORITHM = "rollforward-postcondition-v1"

    @classmethod
    def _cell_state(cls, tc: Any) -> CellState:
        tcPr = tc.find(qn("w:tcPr"))
        gs = tcPr.find(qn("w:gridSpan")) if tcPr is not None else None
        vm = tcPr.find(qn("w:vMerge")) if tcPr is not None else None
        shd = tcPr.find(qn("w:shd")) if tcPr is not None else None
        text = "".join(node.text or "" for node in tc.iter(qn("w:t")))
        style_bits = []
        if shd is not None:
            style_bits.append(f"shd:{shd.get(qn('w:fill')) or ''}")
        pStyle_vals = [p.get(qn("w:val")) or "" for p in tc.iter(qn("w:pStyle"))]
        if pStyle_vals:
            style_bits.append("pStyle:" + ",".join(pStyle_vals))
        return CellState(
            text=re.sub(r"\s+", " ", text).strip(),
            grid_span=int(gs.get(qn("w:val")) or "1") if gs is not None else 1,
            v_merge=(vm.get(qn("w:val")) or "continue") if vm is not None else "none",
            style_signature="|".join(style_bits),
        )

    @classmethod
    def table_state(cls, table: Table) -> List[List[CellState]]:
        return [[cls._cell_state(tc) for tc in row._tr.findall(qn("w:tc"))] for row in table.rows]

    @classmethod
    def _digest(cls, state: Sequence[Sequence[CellState]], column_count: int) -> str:
        h = hashlib.sha256()
        h.update(f"{cls.ALGORITHM}|rows:{len(state)}|cols:{column_count}\n".encode("utf-8"))
        for r_idx, row in enumerate(state):
            parts = [
                f"c{c_idx}:{cell.text}:{cell.grid_span}:{cell.v_merge}:{cell.style_signature}"
                for c_idx, cell in enumerate(row)
            ]
            h.update((f"r{r_idx}:" + "|".join(parts) + "\n").encode("utf-8"))
        return h.hexdigest()[:32]

    @classmethod
    def from_table(cls, table: Table) -> str:
        """Semantic postcondition hash of a table as it currently stands."""
        return cls._digest(cls.table_state(table), len(table.columns))

    @classmethod
    def project(
        cls,
        table: Table,
        row_mutations: Sequence[Any],
        prototype_row_idx: int = 1,
    ) -> str:
        """Hash of the table a plan WOULD produce. Does not modify the document.

        Mirrors `OxmlRowCloner`: each new row is a clone of the prototype row
        with the planned cell values substituted, appended in plan order.
        """
        state = cls.table_state(table)
        if not state:
            return cls._digest(state, len(table.columns))

        proto_idx = min(max(prototype_row_idx, 0), len(state) - 1)
        prototype = state[proto_idx]
        projected = [list(r) for r in state]

        for row_mut in sorted(row_mutations, key=lambda rm: rm.row_idx):
            new_row = [
                CellState(text="", grid_span=c.grid_span, v_merge=c.v_merge,
                          style_signature=c.style_signature)
                for c in prototype
            ]
            for cell in row_mut.cells:
                if 0 <= cell.col_idx < len(new_row):
                    base = new_row[cell.col_idx]
                    new_row[cell.col_idx] = CellState(
                        text=re.sub(r"\s+", " ", str(cell.value)).strip(),
                        grid_span=base.grid_span, v_merge=base.v_merge,
                        style_signature=base.style_signature)
            projected.append(new_row)

        return cls._digest(projected, len(table.columns))

    @classmethod
    def project_from_path(
        cls, template_path: Path, table_ordinal: int,
        row_mutations: Sequence[Any], prototype_row_idx: int = 1,
    ) -> str:
        doc = Document(str(template_path))
        return cls.project(doc.tables[table_ordinal], row_mutations, prototype_row_idx)

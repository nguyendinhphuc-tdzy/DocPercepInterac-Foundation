"""GTPS application-layer orchestration: run the hard-coded HMV demo mapping
against uploaded files and return structured results (for api/routes/process.py).

Architecture note (STATUS.md "Quy tắc không được phá vỡ"): this module is the
only place that knows about the GTPS/HMV-specific DEMO_RULES. It calls into
perception/ (geometry extraction) and mapping/ (lineage + write-back), never
the other way around.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from perception.anchor_builder import assign_anchors, parse_anchor_v2  # noqa: E402
from perception.element_classifier import classify_blocks  # noqa: E402
from perception.models import Element  # noqa: E402
from perception.parser import extract_geometry  # noqa: E402
from mapping.demo_mapper import DEMO_RULES, build_xlsx_anchor  # noqa: E402
from mapping.lineage import LineageLogger  # noqa: E402
from mapping.writeback import WritebackEngine  # noqa: E402


@dataclass
class MappedEntry:
    source_anchor: str
    target_anchor: str
    target_value: str
    confidence: float
    timestamp: str
    # Which target_elements[i] this string anchor actually resolved to —
    # computed with the same table-hash self-healing WritebackEngine uses
    # (see _resolve_target_element_index below), so the frontend can
    # highlight the right element without re-deriving drift-resolution
    # logic itself (table_index alone can be stale after self-heal).
    target_element_index: Optional[int] = None


_PARA_ANCHOR_RE = re.compile(r"^para:(\d+)$")


def _build_target_element_lookup(target_elements: list[Element]) -> tuple[dict, dict]:
    """Keys table cells by (table_hash, row, col) rather than table_index —
    table_index alone goes stale exactly when resolve_table_anchor's
    self-healing kicks in (a table reordered/inserted elsewhere shifts
    every later table_index), so matching on it would silently point at
    the wrong element. table_hash is the same identifier the self-heal
    itself keys on, so this stays correct even when the target_anchor
    string's own table_index is stale.
    """
    by_hash_row_col: dict[tuple[str, int, int], int] = {}
    by_paragraph_index: dict[int, int] = {}
    for el in target_elements:
        a = el.anchor
        if getattr(a, "format", None) != "docx":
            continue
        if a.table_index is not None and a.table_hash:
            by_hash_row_col[(a.table_hash, a.row_index, a.col_index)] = el.index
        elif a.paragraph_index is not None:
            by_paragraph_index[a.paragraph_index] = el.index
    return by_hash_row_col, by_paragraph_index


def _resolve_target_element_index(
    t_anchor: str,
    by_hash_row_col: dict[tuple[str, int, int], int],
    by_paragraph_index: dict[int, int],
) -> Optional[int]:
    parsed = parse_anchor_v2(t_anchor)
    if parsed:
        _t_idx, expected_hash, r_idx, c_idx = parsed
        if expected_hash:
            return by_hash_row_col.get((expected_hash, r_idx, c_idx))
        return None  # v1 anchor (no hash) — can't safely match by position alone
    para_match = _PARA_ANCHOR_RE.match(t_anchor)
    if para_match:
        return by_paragraph_index.get(int(para_match.group(1)))
    return None


@dataclass
class MappingResult:
    source_elements: list[Element]
    target_elements: list[Element]
    mapped: list[MappedEntry] = field(default_factory=list)
    patched_docx_path: str | None = None


def run_mapping(source_paths: list[str], target_path: str, output_dir: str) -> MappingResult:
    """Extracts + assigns anchors for every uploaded source file (any
    number — e.g. GTPS's "Local file mapping" needs both FA&RPTs and
    Appendix I) plus the target, then opportunistically applies the GTPS
    demo mapping (DEMO_RULES) on top. Only produces non-zero `mapped`
    entries when a source file happens to match the known HMV fixture (or
    a table-hash-drifted variant, via perception/anchor_builder.py's
    self-healing) — for any other input this still returns real extracted
    elements (with real anchors) across ALL source files and an empty
    `mapped` list, which is the correct outcome for a use case DEMO_RULES
    doesn't know about: anchors are assigned generically for any document
    regardless of function (Tax, Audit, Advisory...); DEMO_RULES is one
    optional, hard-coded rule set for one specific client, not a
    requirement for the extract/review/edit workflow to be useful.
    """
    target_blocks = extract_geometry(target_path)
    target_fmt = Path(target_path).suffix.lower().lstrip(".")
    target_anchors = assign_anchors(target_blocks, target_fmt)
    target_elements = classify_blocks(target_blocks, target_fmt, target_anchors)

    source_elements: list[Element] = []
    source_map: dict[str, Any] = {}
    source_map_origin: dict[str, str] = {}
    index = 0
    for source_path in source_paths:
        blocks = extract_geometry(source_path)
        fmt = Path(source_path).suffix.lower().lstrip(".")
        anchors = assign_anchors(blocks, fmt)
        elements = classify_blocks(blocks, fmt, anchors, start_index=index)
        source_elements.extend(elements)
        index += len(elements)
        for block in blocks:
            if block.get("sheet_name"):
                key = build_xlsx_anchor(block)
                source_map[key] = block["text"]
                source_map_origin[key] = Path(source_path).name

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger = LineageLogger(log_dir=str(out_dir / ".lineage_logs"))

    by_hash_row_col, by_paragraph_index = _build_target_element_lookup(target_elements)

    mapped: list[MappedEntry] = []
    patches: list[tuple[str, Any]] = []
    for source_anchor, demo_target_anchors in DEMO_RULES.items():
        if source_anchor not in source_map:
            continue
        value = source_map[source_anchor]
        for t_anchor in demo_target_anchors:
            record = logger.log_mapping(
                target_anchor=t_anchor,
                target_value=value,
                source_file=source_map_origin[source_anchor],
                source_anchor=source_anchor,
                confidence=1.0,
            )
            mapped.append(
                MappedEntry(
                    source_anchor=record.source_anchor,
                    target_anchor=record.target_anchor,
                    target_value=record.target_value,
                    confidence=record.confidence,
                    timestamp=record.timestamp,
                    target_element_index=_resolve_target_element_index(
                        t_anchor, by_hash_row_col, by_paragraph_index
                    ),
                )
            )
            patches.append((t_anchor, value))

    patched_docx_path = None
    if patches and target_fmt == "docx":
        engine = WritebackEngine()
        patched_docx_path = str(out_dir / f"{Path(target_path).stem}_patched.docx")
        engine.apply_patches_docx(target_path, patches, patched_docx_path)

    return MappingResult(
        source_elements=source_elements,
        target_elements=target_elements,
        mapped=mapped,
        patched_docx_path=patched_docx_path,
    )

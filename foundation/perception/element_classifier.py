"""Classification capability: the "See" step (Layer 1+2: Detect/Parse/See/
Locate — Foundation_Master_Context.md §5 / Foundation_Build_Plan_v3.md §9.2).

Turns a raw GeometryBlock (perception/parser.py — a format-agnostic dict of
text plus structural indices) and its already-assigned Anchor
(perception/anchor_builder.py) into a typed Element (perception/models.py):
assigns an ElementType and a human-readable name. Deterministic, structural
classification only — heading vs. paragraph vs. table cell, inferred purely
from format + style_id/table_index, the same way every other perception/
module works. This module knows nothing about any specific use case (Tax,
Audit, GTPS, ...) and must stay that way — see STATUS.md "Quy tắc không
được phá vỡ".

Classification Layer seam: `classify_blocks()` accepts an optional
`classifier` argument (see the `Classifier` protocol below) so a caller can
plug in an AI/ML model — a user-supplied classifier, not OpenAI/Workbench —
in place of the deterministic baseline `classify_block`, without this module
or any of its callers changing. Building that model is out of scope here;
this only defines where it plugs in.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol

from perception.models import Anchor, Element, ElementType


class Classifier(Protocol):
    """Signature any classifier — deterministic or AI-backed — must satisfy
    to be usable by classify_blocks(). `classify_block` (below) is the
    default implementation; a future user-supplied model wrapper is another.
    """

    def __call__(
        self, block: Mapping[str, Any], index: int, fmt: str, anchor: Anchor
    ) -> Element: ...


def classify_block(block: Mapping[str, Any], index: int, fmt: str, anchor: Anchor) -> Element:
    """Deterministic baseline classifier — the default `Classifier`.

    Labels a GeometryBlock with a display type/name for the Element Index.
    The Anchor itself is core IP (perception/anchor_builder.py) — this
    heuristic is not: it's a minimal, explicit stand-in (style_id prefix /
    presence of table_index) for a real AI-backed classifier, which any
    caller can substitute via classify_blocks(classifier=...).
    """
    text = block.get("text") or ""

    if fmt == "xlsx":
        name = block.get("named_range") or f"{block['sheet_name']}!{block['cell_address']}"
        etype = ElementType.CELL
    elif fmt == "docx":
        if block.get("table_index") is not None:
            etype = ElementType.CELL
            name = f"Table {block['table_index']} · R{block['row_index']}C{block['col_index']}"
        else:
            style_id = block.get("style_id") or ""
            etype = ElementType.HEADING if style_id.lower().startswith("heading") else ElementType.PARA
            name = text[:60] if text else f"Paragraph {block['paragraph_index']}"
    elif fmt == "pdf":
        etype = ElementType.PARA
        name = text[:60] if text else f"Page {block['page']} line"
    else:
        raise ValueError(f"Unsupported format for element classification: {fmt}")

    return Element(index=index, type=etype, name=name, text=text, anchor=anchor, confidence=1.0)


def classify_blocks(
    blocks: list[Mapping[str, Any]],
    fmt: str,
    anchors: list[Anchor],
    start_index: int = 0,
    classifier: Classifier = classify_block,
) -> list[Element]:
    """Assembles the Element Index for one document: pairs each block with
    its anchor (same order, 1:1 — anchors is assumed already assigned via
    perception/anchor_builder.py::assign_anchors) and classifies it,
    numbering elements from `start_index` so callers merging elements
    across multiple source files can keep one continuous index space (see
    applications/gpts/mapping_service.py).

    `classifier` defaults to the deterministic baseline `classify_block`.
    Passing a different one is the integration point for a future AI
    Classification Layer (a user-supplied model, not built here) —
    classify_blocks itself never needs to change.
    """
    return [
        classifier(block, start_index + i, fmt, anchor)
        for i, (block, anchor) in enumerate(zip(blocks, anchors))
    ]

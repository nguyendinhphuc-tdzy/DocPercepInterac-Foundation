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

Classification Layer seam: `Classifier` (below) is a document-level seam —
it receives ALL of a document's blocks/anchors at once, not one block at a
time. This is deliberate: a per-block seam can't see surrounding blocks, so
an AI classifier plugged in at that granularity could never use cross-block
context (e.g. "this heading's section depends on the heading before it") or
batch its calls (one model invocation per document instead of one per
block). `classify_blocks()` is the deterministic baseline implementation of
`Classifier` — a caller holds a `Classifier` (defaulting to
`classify_blocks`) and calls it; a user-supplied AI model (not
OpenAI/Workbench) that implements the same signature is a drop-in
replacement, no dispatcher needed. Building that model is out of scope
here; this only defines where it plugs in.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol

from perception.models import Anchor, Element, ElementType


class Classifier(Protocol):
    """Document-level classification seam.

    Receives every block/anchor of one document in a single call (not one
    block at a time), so an implementation can use cross-block context —
    e.g. inferring a heading's section from neighboring headings, or
    disambiguating a block's role from what precedes/follows it — and can
    batch a single model invocation over the whole document instead of
    calling out once per block. `classify_blocks()` (below) is the
    deterministic baseline implementation; this Protocol is the integration
    point a future user-supplied AI model plugs into as a drop-in
    replacement.
    """

    def __call__(
        self,
        blocks: list[Mapping[str, Any]],
        fmt: str,
        anchors: list[Anchor],
        start_index: int = 0,
    ) -> list[Element]: ...


def classify_block(block: Mapping[str, Any], index: int, fmt: str, anchor: Anchor) -> Element:
    """Deterministic, per-block classification building block.

    Labels a GeometryBlock with a display type/name for the Element Index.
    The Anchor itself is core IP (perception/anchor_builder.py) — this
    heuristic is not: it's a minimal, explicit stand-in (style_id prefix /
    presence of table_index) for real classification. Used by
    classify_blocks() (the baseline Classifier) to classify one block at a
    time; it has no visibility into other blocks in the document, unlike
    the document-level Classifier seam above.
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
) -> list[Element]:
    """Deterministic baseline `Classifier` — assembles the Element Index for
    one document by mapping classify_block() over each (block, anchor) pair,
    in order, numbering elements from `start_index` so callers merging
    elements across multiple source files can keep one continuous index
    space (see applications/gpts/mapping_service.py).

    This function's signature matches the `Classifier` Protocol exactly, so
    it doubles as the default Classifier: a caller holds a reference to a
    Classifier (defaulting to this function) and calls it uniformly,
    whether that reference points here or at a future AI-backed
    implementation — no separate dispatch mechanism is needed.
    """
    return [
        classify_block(block, start_index + i, fmt, anchor)
        for i, (block, anchor) in enumerate(zip(blocks, anchors))
    ]

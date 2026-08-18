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

import uuid
from typing import Any, Mapping, Protocol

from perception.models import Anchor, Element, ElementCapabilities, ElementType, ExtractionLevel

# Fixed namespace so `element_id` is deterministic across re-parses of an
# unchanged document — re-perceiving the same file must yield the same
# element_id for the same logical element (mirrors the Anchor system's own
# "same element, re-derivable" philosophy), not a fresh random uuid4() per
# construction. Anchor content is already the element's stable identity, so
# hashing it (uuid5, not uuid4) is what makes element_id stable rather than
# introducing a second, independent identity scheme.
_ELEMENT_ID_NAMESPACE = uuid.UUID("6f1e2b3a-6f4c-4a2b-9e3d-6b1a2c3d4e5f")


def _stable_element_id(anchor: Anchor) -> str:
    return str(uuid.uuid5(_ELEMENT_ID_NAMESPACE, anchor.model_dump_json()))


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


# Every non-legacy `kind` (see parser.py's GeometryBlock) maps to exactly
# one (ElementType, capabilities-builder) pair here — a block whose `kind`
# isn't in this table (or has no `kind` at all — pre-`kind` callers) falls
# through to the legacy docx/xlsx/pdf inference below, so nothing this
# phase adds can regress an existing caller. New object kinds land in
# ElementType.UNKNOWN with `detected=True, extracted="none"` rather than
# raising or being silently skipped if a future kind string is added here
# without also adding a classification.

def _full_capabilities(*, editable: bool = False) -> ElementCapabilities:
    return ElementCapabilities(detected=True, extracted=ExtractionLevel.FULL, rendered=True, selectable=True, editable=editable)


def _partial_capabilities(*, rendered: bool | None = True, selectable: bool = True) -> ElementCapabilities:
    return ElementCapabilities(detected=True, extracted=ExtractionLevel.PARTIAL, rendered=rendered, selectable=selectable, editable=False)


def _undetected_capabilities() -> ElementCapabilities:
    return ElementCapabilities(detected=True, extracted=ExtractionLevel.NONE, rendered=None, selectable=False, editable=False)


def classify_block(block: Mapping[str, Any], index: int, fmt: str, anchor: Anchor) -> Element:
    """Deterministic, per-block classification building block.

    Labels a GeometryBlock with a display type/name/capabilities for the
    Element Index. The Anchor itself is core IP (perception/anchor_builder.py)
    — this heuristic is not: it's a minimal, explicit stand-in (style_id
    prefix / presence of table_index / `kind`) for real classification. Used
    by classify_blocks() (the baseline Classifier) to classify one block at
    a time; it has no visibility into other blocks in the document, unlike
    the document-level Classifier seam above.
    """
    text = block.get("text") or ""
    kind = block.get("kind")
    extra = block.get("extra") or {}

    # --- New object kinds this phase adds — dispatched by `kind` first,
    # before the legacy per-format inference below. ---
    if kind == "image":
        name = "Image" + (f" ({extra['width']}×{extra['height']}px)" if extra.get("width") and extra.get("height") else "")
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.IMAGE, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=False))

    if kind == "chart":
        chart_type = extra.get("chart_type")
        name = extra.get("chart_title") or (f"Chart ({chart_type})" if chart_type else "Chart")
        # Position/existence is known; series data and full semantic
        # interpretation are not extracted this phase — see phase report.
        # rendered is format-dependent: the XLSX renderer draws a
        # placeholder box for it (not the chart itself, no chart-rendering
        # library integrated this phase), DOCX's docx-preview support for
        # chart rendering is unverified, so both report rendered=False
        # rather than claim visual fidelity that hasn't been confirmed.
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.CHART, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_partial_capabilities(rendered=False, selectable=False))

    if kind == "drawing":
        name = extra.get("name") or "Drawing"
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.DRAWING, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_partial_capabilities(rendered=None, selectable=False))

    if kind in ("header", "footer"):
        etype = ElementType.HEADER if kind == "header" else ElementType.FOOTER
        # docx-preview (rendering/DocxRenderer.tsx) is configured to render
        # headers/footers, but this phase does not extend the DOCX anchor
        # map to reach into that separate rendered region — selectable is
        # honestly False rather than claiming a sync path that isn't wired.
        return Element(index=index, element_id=_stable_element_id(anchor), type=etype, name=kind.capitalize(), text=text, anchor=anchor,
                        confidence=1.0, capabilities=_partial_capabilities(rendered=True, selectable=False))

    if kind in ("footnote", "endnote", "comment"):
        etype = {"footnote": ElementType.FOOTNOTE, "endnote": ElementType.ENDNOTE, "comment": ElementType.COMMENT}[kind]
        note_id = extra.get("note_id")
        author = extra.get("author")
        label = f"{kind.capitalize()} {note_id}" if note_id is not None else kind.capitalize()
        if author:
            label += f" ({author})"
        # docx-preview renders footnotes/endnotes inline (renderFootnotes/
        # renderEndnotes: true) but comments are not rendered by it at all —
        # none of the three are anchor-mapped to a DOM region this phase.
        return Element(index=index, element_id=_stable_element_id(anchor), type=etype, name=label, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_partial_capabilities(rendered=(kind != "comment"), selectable=False))

    if kind == "pdf_image":
        name = "Image" + (f" ({extra['width']}×{extra['height']}px)" if extra.get("width") and extra.get("height") else "")
        # The rendered PDF page (pdf.js canvas) already shows the image —
        # this Element is a selectable identity over that already-rendered
        # region (rendering/PdfRenderer.tsx's overlay loop is generic over
        # any element with a pdf anchor, images included, no renderer change
        # needed), not a second rendering of it.
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.IMAGE, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=False))

    if kind == "annotation":
        subtype = extra.get("subtype", "unknown")
        name = f"Link: {text[:50]}" if subtype == "link" and text else f"Annotation ({subtype})"
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.ANNOTATION, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=False))

    if kind == "page_fallback":
        return Element(index=index, element_id=_stable_element_id(anchor), type=ElementType.PAGE, name=f"Page {block.get('page')}", text=text, anchor=anchor,
                        confidence=1.0, capabilities=_undetected_capabilities())

    # --- Legacy per-format inference (unchanged behavior) for
    # paragraph/table_cell/cell/text_line blocks, and as a fallback for any
    # block a future caller constructs without a `kind` at all. ---
    if fmt == "xlsx":
        name = block.get("named_range") or f"{block['sheet_name']}!{block['cell_address']}"
        etype = ElementType.CELL
        return Element(index=index, element_id=_stable_element_id(anchor), type=etype, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=True))
    elif fmt == "docx":
        if block.get("table_index") is not None:
            etype = ElementType.CELL
            name = f"Table {block['table_index']} · R{block['row_index']}C{block['col_index']}"
        else:
            style_id = block.get("style_id") or ""
            etype = ElementType.HEADING if style_id.lower().startswith("heading") else ElementType.PARA
            name = text[:60] if text else f"Paragraph {block['paragraph_index']}"
        return Element(index=index, element_id=_stable_element_id(anchor), type=etype, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=True))
    elif fmt == "pdf":
        etype = ElementType.PARA
        name = text[:60] if text else f"Page {block['page']} line"
        # PDF write-back does not exist (output/writeback.py has no PDF
        # handler) — never claim editable=True for a format that can't
        # actually be saved.
        return Element(index=index, element_id=_stable_element_id(anchor), type=etype, name=name, text=text, anchor=anchor,
                        confidence=1.0, capabilities=_full_capabilities(editable=False))
    else:
        raise ValueError(f"Unsupported format for element classification: {fmt}")


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

"""Locate capability: build + resolve stable Anchors for parsed elements.

This is the project's core IP (Foundation_Master_Context.md §5 "Anchor
System — IP của dự án") — the mechanism that lets an element be found again
in a document that has since been edited, without any AI involved:

    file_intake -> extract_geometry (parser.py) -> assign_anchors (here)

Two responsibilities, kept separate:

- **assign_*`** — given a freshly parsed GeometryBlock, build its Anchor.
  Deterministic, format-specific, no knowledge of any particular client or
  use case (that would belong in applications/, per STATUS.md's
  architecture rule).
- **resolve_*`** — given an Anchor recorded from a previous parse and a new
  (possibly edited) copy of the same document, find the element again.
  This is what P3-04 tests: resolving must survive structural drift
  (paragraphs inserted/removed, tables reordered) and must never silently
  return the wrong element — it either finds the right one or raises.

Resolution ladder per format (Foundation_Master_Context.md §5):

    DOCX paragraph: Strategy 1 style_id+text_fingerprint (best)
                    Strategy 2 paragraph_index+style_id (fallback)
                    Strategy 3 paragraph_index only (warn, last resort)
                    FAIL -> raise ValueError
    DOCX table cell: table_hash (SHA256 of header row) + self-heal re-scan
                      if the table has moved — see resolve_table_anchor().
    XLSX: named_range takes priority over cell_address; no ladder needed —
          cell_address is stable enough for digital files (STATUS.md).
    PDF: position-based only (page + reading_order_index, bbox fallback) —
         real financial PDFs repeat boilerplate text across many pages
         (see tests/test_parser.py), so text-content matching is unsafe;
         AnchorPDF deliberately has no text_fingerprint field.
"""
from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING, Any, Optional, Tuple

from perception.models import AnchorDOCX, AnchorPDF, AnchorXLSX, Anchor

if TYPE_CHECKING:
    from perception.parser import GeometryBlock


# --- DOCX table-cell anchors (moved unchanged from mapping/anchor_builder.py) ---


def build_table_hash(table) -> str:
    """Creates a fingerprint (hash) based on the first row of a DOCX table."""
    if not table.rows:
        return "empty"

    # Concatenate all cell text in the first row
    header_text = "".join([cell.text.strip() for cell in table.rows[0].cells])

    # Compute SHA256, keep first 8 chars for brevity
    fingerprint = hashlib.sha256(header_text.encode('utf-8')).hexdigest()[:8]
    return fingerprint


def parse_anchor_v2(anchor_str: str) -> Optional[Tuple[int, Optional[str], int, int]]:
    """Parses Anchor v2 format: table:[idx]:[hash]_row:[r]_col:[c]
       Falls back to parsing v1: table:[idx]_row:[r]_col:[c] if hash is missing.
    """
    # Try v2 first: table:6:a1b2c3d4_row:1_col:4
    match_v2 = re.match(r"table:(\d+):([a-z0-9]+)_row:(\d+)_col:(\d+)", anchor_str)
    if match_v2:
        return int(match_v2.group(1)), match_v2.group(2), int(match_v2.group(3)), int(match_v2.group(4))

    # Try v1 fallback: table:6_row:1_col:4
    match_v1 = re.match(r"table:(\d+)_row:(\d+)_col:(\d+)", anchor_str)
    if match_v1:
        return int(match_v1.group(1)), None, int(match_v1.group(2)), int(match_v1.group(3))

    return None


def resolve_table_anchor(doc, anchor_str: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Resolves the exact DOCX Table Cell given an anchor string, with Anti-Drift capability.
    Returns (cell_object, healing_message)
    """
    parsed = parse_anchor_v2(anchor_str)
    if not parsed:
        return None, "Invalid anchor format"

    t_idx, expected_hash, r_idx, c_idx = parsed

    # 1. Fast Path (No drift)
    try:
        table = doc.tables[t_idx]
        current_hash = build_table_hash(table)

        # If hash is matched or we don't have an expected hash (v1 anchor), proceed
        if not expected_hash or current_hash == expected_hash:
            return table.rows[r_idx].cells[c_idx], None
    except IndexError:
        pass  # Table count might have decreased

    # 2. Self-healing Path (Drift detected)
    if expected_hash:
        for i, table in enumerate(doc.tables):
            if build_table_hash(table) == expected_hash:
                try:
                    return table.rows[r_idx].cells[c_idx], f"Drift detected. Self-healed from table {t_idx} to table {i}"
                except IndexError:
                    return None, f"Drift detected, found table {i} but invalid row/col indices."

    # 3. Fallback / Failure
    return None, "Failed to resolve anchor (Hash not found or table missing)"


def _text_fingerprint(text: str) -> str:
    return hashlib.sha256((text or "")[:50].encode("utf-8")).hexdigest()[:8]


# --- Assign: GeometryBlock -> Anchor -----------------------------------------


_DOCX_MEDIA_KINDS = {"image", "chart", "drawing"}
_DOCX_CHROME_KINDS = {"header", "footer", "footnote", "endnote", "comment"}


def assign_docx_anchor(
    block: "GeometryBlock", all_blocks: "Optional[list[GeometryBlock]]" = None
) -> AnchorDOCX:
    """Paragraph anchor (paragraph_index+style_id+text_fingerprint), table-
    cell anchor (table_index+table_hash+row_index+col_index), or a media/
    chrome anchor — per the block's `kind` (falling back to the pre-`kind`
    inference — table_index presence — for callers passing an older block
    shape, though extract_geometry always sets `kind` now).

    `all_blocks`, when given (assign_anchors passes the full document's
    blocks), lets a paragraph anchor also record `duplicate_ordinal` — its
    rank among other paragraphs sharing the exact same (style_id,
    text_fingerprint). Real documents genuinely have this (e.g. a caption
    like "Source: TP Cat database" repeated under every table) and
    uneven drift — an insertion between two occurrences — breaks a plain
    "nearest paragraph_index" tie-break, since the two occurrences don't
    shift by the same amount. Ordinal rank is immune to that: insertions
    elsewhere don't reorder the existing occurrences of the same signature.
    """
    kind = block.get("kind")
    extra = block.get("extra") or {}

    if kind in _DOCX_MEDIA_KINDS:
        # Identity is the OOXML relationship (survives a re-save far more
        # reliably than paragraph position — see AnchorDOCX field comment).
        # media_id == relationship_id for images specifically — that IS the
        # docx media manifest's key (see parser.py::_docx_media_manifest) —
        # so a consumer never needs to know the two happen to coincide.
        rel_id = extra.get("relationship_id")
        return AnchorDOCX(
            paragraph_index=block.get("paragraph_index"),
            style_id="",
            text_fingerprint="",
            relationship_id=rel_id,
            drawing_id=str(extra.get("drawing_id")) if extra.get("drawing_id") is not None else None,
            media_id=rel_id if kind == "image" else None,
        )

    if kind in _DOCX_CHROME_KINDS:
        # Headers/footers/footnotes/endnotes/comments live in separate OOXML
        # parts, outside body paragraph order — text_fingerprint is still
        # their most stable identity (there is no body paragraph_index for
        # them), disambiguated by drawing_id carrying the note/comment id.
        note_id = extra.get("note_id")
        return AnchorDOCX(
            paragraph_index=None,
            style_id=kind,  # repurposed as a coarse type tag for this anchor family — never compared against a real Word style
            text_fingerprint=_text_fingerprint(block.get("text") or ""),
            drawing_id=str(note_id) if note_id is not None else None,
        )

    fingerprint = _text_fingerprint(block.get("text") or "")
    if block.get("table_index") is not None:
        return AnchorDOCX(
            paragraph_index=None,
            style_id=block.get("style_id") or "",
            text_fingerprint=fingerprint,
            table_index=block["table_index"],
            table_hash=block.get("table_hash"),
            row_index=block["row_index"],
            col_index=block["col_index"],
        )

    style_id = block.get("style_id") or ""
    duplicate_ordinal = None
    if all_blocks is not None:
        ordinal = 0
        for b in all_blocks:
            if b.get("kind") not in (None, "paragraph"):
                continue
            if b.get("table_index") is not None:
                continue
            if (b.get("style_id") or "") != style_id:
                continue
            if _text_fingerprint(b.get("text") or "") != fingerprint:
                continue
            if b is block:
                duplicate_ordinal = ordinal
                break
            ordinal += 1

    return AnchorDOCX(
        paragraph_index=block["paragraph_index"],
        style_id=style_id,
        text_fingerprint=fingerprint,
        duplicate_ordinal=duplicate_ordinal,
    )


def assign_xlsx_anchor(block: "GeometryBlock") -> AnchorXLSX:
    row_label = block.get("row_label")
    extra = block.get("extra") or {}
    if block.get("kind") in ("image", "chart"):
        drawing_id = extra.get("drawing_id")
        return AnchorXLSX(
            sheet_name=block["sheet_name"],
            cell_address=block["cell_address"],
            drawing_id=drawing_id,
            from_cell=extra.get("from_cell"),
            to_cell=extra.get("to_cell"),
            # drawing_id IS the xlsx media manifest key for images (see
            # parser.py::_xlsx_media_manifest) — charts have no manifest entry.
            media_id=drawing_id if block.get("kind") == "image" else None,
        )
    return AnchorXLSX(
        sheet_name=block["sheet_name"],
        cell_address=block["cell_address"],
        named_range=block.get("named_range"),
        row_label_fingerprint=_text_fingerprint(row_label) if row_label else None,
    )


def assign_pdf_anchors(blocks: list["GeometryBlock"]) -> list[AnchorPDF]:
    """Reading order resets per page (matches the worked example in
    Foundation_Master_Context.md §5) so position comparisons during resolve
    stay meaningful even in very long documents."""
    anchors: list[AnchorPDF] = []
    per_page_counter: dict[int, int] = {}
    for block in blocks:
        page = block["page"]
        order = per_page_counter.get(page, 0)
        per_page_counter[page] = order + 1

        x0, top, x1, bottom = block["bbox"]
        page_width = block["page_width"] or 1.0
        page_height = block["page_height"] or 1.0
        bbox_relative = (
            x0 / page_width,
            top / page_height,
            (x1 - x0) / page_width,
            (bottom - top) / page_height,
        )
        anchors.append(
            AnchorPDF(page=page, bbox_relative=bbox_relative, reading_order_index=order)
        )
    return anchors


def assign_anchors(blocks: list["GeometryBlock"], fmt: str) -> list[Anchor]:
    """Format dispatcher — mirrors parser.py::extract_geometry's own
    dispatch-by-extension pattern."""
    if fmt == "docx":
        return [assign_docx_anchor(b, blocks) for b in blocks]
    if fmt == "xlsx":
        return [assign_xlsx_anchor(b) for b in blocks]
    if fmt == "pdf":
        return assign_pdf_anchors(blocks)
    raise ValueError(f"Unsupported format for anchor assignment: {fmt}")


# --- Resolve: Anchor (from a previous parse) -> element in a new parse ------


def resolve_paragraph_anchor(doc, anchor: AnchorDOCX) -> Tuple[Optional[Any], Optional[str]]:
    """Strategy 1/2/3 ladder for non-table DOCX anchors
    (Foundation_Master_Context.md §5)."""
    paragraphs = doc.paragraphs

    # Strategy 1: style_id + text_fingerprint match — content-based, survives
    # paragraphs being inserted/removed elsewhere in the document.
    matches = []
    for i, p in enumerate(paragraphs):
        if not p.text.strip():
            continue
        style_id = p.style.style_id if p.style else ""
        if style_id == anchor.style_id and _text_fingerprint(p.text) == anchor.text_fingerprint:
            matches.append((i, p))
    if matches:
        if anchor.duplicate_ordinal is not None and anchor.duplicate_ordinal < len(matches):
            # Rank-based disambiguation — robust even under uneven drift
            # (an insertion between two occurrences of the same repeated
            # signature), unlike proximity-to-paragraph_index below.
            return matches[anchor.duplicate_ordinal][1], None
        if anchor.paragraph_index is not None:
            # Fallback for anchors with no duplicate_ordinal recorded
            # (table cells never reach here; pre-2026-08-13 anchors might).
            # Proximity to the originally recorded position — works for
            # uniform drift, can mis-rank under uneven drift between
            # occurrences (see duplicate_ordinal above for the real fix).
            matches.sort(key=lambda pair: abs(pair[0] - anchor.paragraph_index))
        return matches[0][1], None

    # Strategy 2: paragraph_index + style_id — position + type, content may
    # have changed under us.
    if anchor.paragraph_index is not None and anchor.paragraph_index < len(paragraphs):
        p = paragraphs[anchor.paragraph_index]
        style_id = p.style.style_id if p.style else ""
        if style_id == anchor.style_id:
            return p, "Strategy 2: matched by paragraph_index+style_id — text content differs from the recorded anchor"

    # Strategy 3: paragraph_index only — last resort.
    if anchor.paragraph_index is not None and anchor.paragraph_index < len(paragraphs):
        return paragraphs[anchor.paragraph_index], "Strategy 3: matched by paragraph_index only — style/content may differ, low confidence"

    return None, None  # caller raises — see resolve_docx_anchor


def resolve_docx_anchor(doc, anchor: AnchorDOCX) -> Tuple[Optional[Any], Optional[str]]:
    """Dispatches to the table-cell resolver (reuses resolve_table_anchor's
    existing anti-drift string format) or the paragraph ladder, then raises
    if neither found anything — an anchor that can't be resolved must never
    be reported as a silent match."""
    if anchor.table_index is not None:
        if anchor.table_hash:
            anchor_str = f"table:{anchor.table_index}:{anchor.table_hash}_row:{anchor.row_index}_col:{anchor.col_index}"
        else:
            anchor_str = f"table:{anchor.table_index}_row:{anchor.row_index}_col:{anchor.col_index}"
        result, message = resolve_table_anchor(doc, anchor_str)
    else:
        result, message = resolve_paragraph_anchor(doc, anchor)

    if result is None:
        raise ValueError(f"Failed to resolve DOCX anchor: {anchor!r} — no strategy matched")
    return result, message


def _row_label_fingerprint(ws, row_number: int) -> Optional[str]:
    label = next((str(c.value).strip() for c in ws[row_number] if c.value is not None), None)
    return _text_fingerprint(label) if label else None


_CELL_COLUMN_RE = re.compile(r"[A-Za-z]+")


def resolve_xlsx_anchor(wb, anchor: AnchorXLSX) -> Tuple[Any, Optional[str]]:
    """named_range takes priority per the Anchor schema (fast path, most
    trustworthy — Excel/openpyxl keeps a defined name's reference in sync
    when rows/columns are inserted). Otherwise: direct cell_address lookup,
    corroborated by `row_label_fingerprint` — the recorded row's leftmost
    non-empty cell (STATUS.md's original "cell_address is stable enough"
    decision holds only while the sheet's *rows* haven't shifted; row
    insert/delete silently breaks a plain cell_address, so this checks for
    that and self-heals by re-scanning the same column for the row whose
    label now matches, same idea as resolve_table_anchor's table-hash heal
    for DOCX)."""
    if anchor.named_range:
        defined_name = wb.defined_names.get(anchor.named_range)
        if defined_name is not None:
            for sheet_name, coord in defined_name.destinations:
                return wb[sheet_name][coord.split(":")[0]], None

    try:
        ws = wb[anchor.sheet_name]
    except KeyError as exc:
        raise ValueError(f"Failed to resolve XLSX anchor: {anchor!r} — sheet not found: {exc}") from exc

    try:
        cell = ws[anchor.cell_address]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Failed to resolve XLSX anchor: {anchor!r} — {exc}") from exc

    if anchor.row_label_fingerprint is None or _row_label_fingerprint(ws, cell.row) == anchor.row_label_fingerprint:
        return cell, None

    # Self-heal: this row's label no longer matches what was recorded —
    # rows have likely been inserted/removed above it. Re-scan the same
    # column for the row whose label matches now.
    column_match = _CELL_COLUMN_RE.match(anchor.cell_address)
    col_letter = column_match.group(0) if column_match else None
    if col_letter:
        for row in ws.iter_rows():
            row_number = row[0].row
            if _row_label_fingerprint(ws, row_number) == anchor.row_label_fingerprint:
                return ws[f"{col_letter}{row_number}"], f"Drift detected. Self-healed row {cell.row} -> {row_number} by row label"

    raise ValueError(
        f"Failed to resolve XLSX anchor: {anchor!r} — row label drifted and no matching row found"
    )


_PDF_BBOX_TOLERANCE = 0.02  # relative units — ~same line position


def resolve_pdf_anchor(
    blocks: list["GeometryBlock"], anchor: AnchorPDF
) -> Tuple[Optional["GeometryBlock"], Optional[str]]:
    """Position-based only, deliberately — see module docstring. Strategy 1
    requires the (page, reading_order_index) match to also land at roughly
    the recorded bbox — index alone isn't trustworthy once content has
    shifted, since a *different* block can slide into the old index.
    Strategy 2 falls back to nearest bbox on the same page, ignoring
    reading order, for when insertions have shifted it."""
    fresh_anchors = assign_pdf_anchors(blocks)
    candidates = [
        (block, a) for block, a in zip(blocks, fresh_anchors) if a.page == anchor.page
    ]
    if not candidates:
        raise ValueError(f"Failed to resolve PDF anchor: {anchor!r} — no blocks on page {anchor.page}")

    def distance(a: AnchorPDF) -> float:
        ax, ay, _, _ = a.bbox_relative
        bx, by, _, _ = anchor.bbox_relative
        return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

    for block, a in candidates:
        if a.reading_order_index == anchor.reading_order_index and distance(a) <= _PDF_BBOX_TOLERANCE:
            return block, None

    nearest_block, _ = min(candidates, key=lambda pair: distance(pair[1]))
    return nearest_block, "Strategy 2: matched by nearest bbox on the same page — reading order shifted"

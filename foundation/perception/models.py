"""Pydantic schemas for Document Perception (Layer 1+2: Detect/Parse/See/Locate).

Schema matches Foundation_Build_Plan.md section 3 (Element Index + Anchor +
Profile) — the version reconciled against the latest approved presentation
deck, superseding the earlier draft in Foundation_Master_Context.md.

Every other module in perception/, adapters/, and api/ depends on these models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    """Structural primitives ONLY. Semantic/business roles (e.g. "glossary")
    belong to the application layer and are assigned via `Element.tags`.

    This is a taxonomy of everything Foundation can *represent*, not a
    promise that every value is fully extracted/rendered/editable for
    every format that can contain it — see `ElementCapabilities` on each
    `Element` for what's actually true of that specific instance. A value
    existing here is what makes "detected but not fully understood"
    possible in the first place (see element_classifier.py's `_UNKNOWN`
    fallback) instead of an unrecognized object being silently dropped by
    the parser.

    Values kept from the original 5-value taxonomy (HEADING/TABLE/CELL/
    PARA/PICTURE) are unchanged on purpose — every existing anchor,
    fixture and test that names them stays valid. New values only add.
    """

    # Structural containers
    DOCUMENT = "document"
    PAGE = "page"
    SECTION = "section"

    # Text
    HEADING = "heading"
    PARA = "para"
    PARAGRAPH = "para"  # alias of PARA — brief's requested name, same wire value, no migration needed
    RUN = "run"  # declared, not yet extracted (sub-paragraph formatting spans) — see phase report
    LIST = "list"  # declared, not yet extracted — see phase report
    LIST_ITEM = "list_item"  # declared, not yet extracted — see phase report
    HYPERLINK = "hyperlink"
    BOOKMARK = "bookmark"  # declared, not yet extracted — see phase report

    # Tables
    TABLE = "table"  # declared; tables are not yet materialized as their own Element (only their cells are) — see phase report
    TABLE_ROW = "table_row"  # declared, not yet extracted — see phase report
    CELL = "cell"

    # Media
    PICTURE = "picture"  # legacy alias, superseded by IMAGE below — kept so old data/tests referencing it still validate
    IMAGE = "image"
    CHART = "chart"
    DRAWING = "drawing"
    SHAPE = "shape"  # declared; DOCX/XLSX drawings that are neither a picture nor a recognized chart classify as DRAWING, not SHAPE, this phase — see phase report
    TEXT_BOX = "text_box"  # declared, not yet distinguished from DRAWING — see phase report
    EMBEDDED_OBJECT = "embedded_object"  # declared, not yet extracted — see phase report

    # Document chrome
    HEADER = "header"
    FOOTER = "footer"
    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"
    COMMENT = "comment"
    PAGE_BREAK = "page_break"  # declared, not yet extracted — see phase report
    SECTION_BREAK = "section_break"  # declared, not yet extracted — see phase report

    # PDF-specific
    ANNOTATION = "annotation"
    FORM_FIELD = "form_field"  # declared, not yet extracted — see phase report

    # Fallback — an object was detected but this phase has no specific
    # classification for it. MUST be used instead of silently dropping the
    # object (see element_classifier.py's unknown-drawing handling).
    UNKNOWN = "unknown"


class ExtractionLevel(str, Enum):
    """How completely `Element.text`/geometry/semantics were pulled from the
    source — independent of whether the object could be *detected* at all
    (see `ElementCapabilities.detected`, which is always true once an
    Element exists for it)."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class ElementCapabilities(BaseModel):
    """What Foundation actually knows how to do with this specific element
    instance — distinct per element, not per ElementType, since e.g. a DOCX
    chart is `extracted="partial"` (position/type known, series data isn't)
    while an XLSX cell is `extracted="full"`. Consumers (frontend, future
    Agent/application layers) must check this rather than assume every
    element of a given type behaves the same way.

    `detected=True` is the one invariant every Element in this system
    satisfies by construction — an object Foundation could not even detect
    never becomes an Element in the first place, and one it detected but
    could not classify becomes `ElementType.UNKNOWN` rather than being
    silently dropped (see element_classifier.py)."""

    detected: bool = True
    extracted: ExtractionLevel = ExtractionLevel.FULL
    # None = "not applicable to this element in this renderer" (e.g. a
    # footnote/comment isn't a distinct visually-locatable region the
    # current renderers map to yet) rather than "known to not render".
    rendered: Optional[bool] = True
    selectable: bool = True
    editable: bool = False


class AnchorDOCX(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: Optional[int] = None  # None for table-cell/media anchors
    style_id: str = ""
    text_fingerprint: str = ""  # sha256(text[:50])[:8] — empty for media anchors (no text identity)
    # 0-indexed rank among all paragraphs sharing this exact
    # (style_id, text_fingerprint) signature, top-to-bottom — disambiguates
    # repeated boilerplate (e.g. a caption reused under every table) when
    # paragraph_index has drifted unevenly. None for table-cell anchors and
    # for anchors built before this field existed.
    duplicate_ordinal: Optional[int] = None
    table_index: Optional[int] = None
    table_hash: Optional[str] = None
    row_index: Optional[int] = None
    col_index: Optional[int] = None
    # Media/drawing identity (images, charts, unrecognized drawings) — an
    # *extension* of this same anchor shape rather than a second discriminated
    # "docx" variant, since Pydantic's `Field(discriminator="format")` needs
    # exactly one shape per discriminator value; every consumer that already
    # pattern-matches on `anchor.format == "docx"` keeps working unchanged.
    # `relationship_id` (the r:id / r:embed OOXML relationship) is the
    # primary stable identity for a drawing — it survives the document being
    # re-saved by Word even if paragraph_index shifts, since Word preserves
    # relationship IDs far more reliably than exact paragraph position.
    relationship_id: Optional[str] = None
    drawing_id: Optional[str] = None  # docPr id — disambiguates multiple drawings sharing one relationship_id (rare)
    media_id: Optional[str] = None  # ElementIndex.media[] key — see MediaAsset
    # Footnote/endnote/comment identity — the OOXML `w:id` from footnotes.xml
    # / endnotes.xml / comments.xml. A typed field of its own rather than
    # reusing `drawing_id` (an earlier version of this anchor did exactly
    # that, since both are "just an id string") — `drawing_id` specifically
    # means docPr id and a footnote has no docPr at all; overloading it blurs
    # what field a given consumer should even look at. docx-preview's own
    # parsed footnote/endnote objects carry this same `w:id` as `.id`
    # (frontend/src/components/document/rendering/DocxRenderer.tsx stamps it
    # as `data-note-id`), giving an exact identity match instead of the
    # text-content matching every other chrome kind is stuck with.
    note_id: Optional[str] = None


class AnchorXLSX(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str  # A1 notation, e.g. "B14" — for a drawing/chart anchor, its `from_cell` (see below)
    named_range: Optional[str] = None  # takes priority over cell_address if set
    # sha256(row label)[:8], where "row label" = this row's leftmost
    # non-empty cell (the typical financial-statement convention: a line
    # item name in column A/B, values to the right). Lets resolve_xlsx_anchor
    # detect and self-heal row insert/delete drift — cell_address alone
    # can't (see perception/anchor_builder.py).
    row_label_fingerprint: Optional[str] = None
    # Drawing identity (images/charts) — extends this same anchor shape for
    # the same reason as AnchorDOCX above. `drawing_id` is this sheet's
    # openpyxl drawing-part-relative index; `from_cell`/`to_cell` are the
    # two-cell anchor range a real spreadsheet app would show the object
    # spanning (cell_address alone, the top-left, would visually reproduce
    # only a 1x1-cell object).
    drawing_id: Optional[str] = None
    from_cell: Optional[str] = None
    to_cell: Optional[str] = None
    media_id: Optional[str] = None  # ElementIndex.media[] key — see MediaAsset


class AnchorPDF(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int = Field(ge=1)
    bbox_relative: tuple[float, float, float, float]  # (x, y, w, h), scale 0-1, not pixels
    reading_order_index: int


Anchor = Union[AnchorDOCX, AnchorXLSX, AnchorPDF]


class MediaAsset(BaseModel):
    """One entry in `ElementIndex.media` — metadata only, never the binary
    itself (see api/routes/documents.py's media endpoint, which resolves
    `media_id` back to the actual bytes on demand, scoped to that one
    document's own package). `source_reference` is an opaque, package-
    internal locator (e.g. "docx:word/media/image1.png" — a path *inside*
    the uploaded file's own ZIP, not a filesystem path) that only the
    server ever resolves; it must never be treated as a servable path by
    itself without re-validating it against that document's actual media
    parts at request time."""

    media_id: str
    type: Literal["image", "chart"]
    mime_type: str
    width: Optional[int] = None  # px
    height: Optional[int] = None  # px
    source_reference: str


class Element(BaseModel):
    """One row of the Element Index — the Middle Output."""

    index: int  # "#" — position within the document (legacy identity, still required by the current UI)
    element_id: str = Field(default_factory=lambda: str(uuid.uuid4()))  # stable identity — survives reordering, unlike `index`
    parent_id: Optional[str] = None  # `element_id` of a containing element, where a real parent Element exists (see phase report — not populated for every relationship yet)
    section: Optional[str] = None  # parent section, e.g. "Assets", "Notes"
    type: ElementType
    name: str  # human-readable label, e.g. "Table 2", "Note 1: basis"
    text: str = ""
    text_normalized: Optional[str] = None
    source: Literal["text_layer", "ocr", "manual"] = "text_layer"
    anchor: Anchor = Field(discriminator="format")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)  # application-assigned semantic roles, e.g. ["glossary"]
    capabilities: ElementCapabilities = Field(default_factory=ElementCapabilities)


class WorksheetMetadata(BaseModel):
    """Sheet-level facts an XLSX renderer needs that don't belong to any one
    cell — kept separate from `Element` on purpose (see perception/parser.py
    module docstring): a merged range or a hidden row isn't itself a
    perceivable document *object* the way a cell/image/chart is, it's a
    display fact about the grid. Populated once per sheet, keyed by name on
    `ElementIndex.worksheets`."""

    sheet_name: str
    merged_ranges: list[str] = Field(default_factory=list)  # e.g. ["A1:C1", "B4:B6"]
    hidden_rows: list[int] = Field(default_factory=list)
    hidden_columns: list[str] = Field(default_factory=list)  # column letters
    row_heights: dict[int, float] = Field(default_factory=dict)  # only rows with an explicit (non-default) height
    column_widths: dict[str, float] = Field(default_factory=dict)  # only columns with an explicit (non-default) width
    freeze_panes: Optional[str] = None  # e.g. "B2", or None if not frozen


class ElementIndex(BaseModel):
    """The full Element Index for one parsed document."""

    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    format: str
    elements: list[Element] = Field(default_factory=list)
    media: list[MediaAsset] = Field(default_factory=list)
    worksheets: list[WorksheetMetadata] = Field(default_factory=list)  # xlsx only — empty for docx/pdf
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ProfileField(BaseModel):
    field_name: str
    match_rule: Literal["label", "structural", "fingerprint"]
    anchor_pattern: dict  # pattern used to recognize this field in same-type documents
    formula: Optional[str] = None


class Profile(BaseModel):
    profile_id: str
    version: int  # bumped each time a reviewer clarifies a new field
    document_type: str
    fields: list[ProfileField] = Field(default_factory=list)
    coverage_pct: Optional[float] = None  # computed from Scale Pipeline

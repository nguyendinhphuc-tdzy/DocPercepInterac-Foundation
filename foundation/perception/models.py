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
    belong to the application layer and are assigned via `Element.tags`."""

    HEADING = "heading"
    TABLE = "table"
    CELL = "cell"
    PARA = "para"
    PICTURE = "picture"


class AnchorDOCX(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: Optional[int] = None  # None for table-cell anchors
    style_id: str
    text_fingerprint: str  # sha256(text[:50])[:8]
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


class AnchorXLSX(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str  # A1 notation, e.g. "B14"
    named_range: Optional[str] = None  # takes priority over cell_address if set
    # sha256(row label)[:8], where "row label" = this row's leftmost
    # non-empty cell (the typical financial-statement convention: a line
    # item name in column A/B, values to the right). Lets resolve_xlsx_anchor
    # detect and self-heal row insert/delete drift — cell_address alone
    # can't (see perception/anchor_builder.py).
    row_label_fingerprint: Optional[str] = None


class AnchorPDF(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int = Field(ge=1)
    bbox_relative: tuple[float, float, float, float]  # (x, y, w, h), scale 0-1, not pixels
    reading_order_index: int


Anchor = Union[AnchorDOCX, AnchorXLSX, AnchorPDF]


class Element(BaseModel):
    """One row of the Element Index — the Middle Output."""

    index: int  # "#" — position within the document
    section: Optional[str] = None  # parent section, e.g. "Assets", "Notes"
    type: ElementType
    name: str  # human-readable label, e.g. "Table 2", "Note 1: basis"
    text: str = ""
    text_normalized: Optional[str] = None
    source: Literal["text_layer", "ocr", "manual"] = "text_layer"
    anchor: Anchor = Field(discriminator="format")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)  # application-assigned semantic roles, e.g. ["glossary"]


class ElementIndex(BaseModel):
    """The full Element Index for one parsed document."""

    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    format: str
    elements: list[Element] = Field(default_factory=list)
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

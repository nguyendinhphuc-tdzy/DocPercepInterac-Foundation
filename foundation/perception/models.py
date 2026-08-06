"""Pydantic schemas for Document Perception (Layer 1+2: Detect/Parse/See/Locate).

Every other module in perception/, adapters/, and api/ depends on these models.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class ElementType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    TABLE_CELL = "table_cell"
    LIST_ITEM = "list_item"
    PICTURE = "picture"
    GLOSSARY = "glossary"
    FOOTER = "footer"
    HEADER = "header"
    CAPTION = "caption"


class BoundingBox(BaseModel):
    page: int
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(ge=0.0, le=1.0)
    h: float = Field(ge=0.0, le=1.0)


class DocxAnchor(BaseModel):
    format: Literal["docx"] = "docx"
    paragraph_index: int
    style_id: Optional[str] = None
    text_fingerprint: str
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    col_index: Optional[int] = None


class XlsxAnchor(BaseModel):
    format: Literal["xlsx"] = "xlsx"
    sheet_name: str
    cell_address: str
    named_range: Optional[str] = None


class PdfAnchor(BaseModel):
    format: Literal["pdf"] = "pdf"
    page: int = Field(ge=1)
    bbox: BoundingBox
    reading_order_index: int


Anchor = Union[DocxAnchor, XlsxAnchor, PdfAnchor]


class FoundationElement(BaseModel):
    element_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ElementType
    text: Optional[str] = None
    level: Optional[int] = None
    section: Optional[str] = None
    anchor: Anchor = Field(discriminator="format")
    bbox: Optional[BoundingBox] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    style: dict = Field(default_factory=dict)
    children: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class FoundationDocument(BaseModel):
    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str
    format: str
    title: Optional[str] = None
    page_count: int
    elements: list[FoundationElement] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    docling_version: str

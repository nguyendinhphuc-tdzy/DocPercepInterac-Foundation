"""
XLSX visual-object inventory (Phase PROD-UX-1, audit only)
==========================================================
Location: foundation/perception/xlsx_visual_inventory.py

Answers one question honestly: **which drawing objects does a workbook contain,
and which of them survive into what the user sees?**

This module deliberately implements NO rendering. It is read-only forensics over
the OOXML package, added so the UI can state what it cannot draw instead of
presenting a partial worksheet as if it were complete.

Why objects go missing today
----------------------------
`perception/parser.py` reads workbooks through openpyxl, which exposes exactly
two members of a sheet's drawing part:

    ws._images   -> `<xdr:pic>` pictures
    ws._charts   -> `<xdr:graphicFrame>` frames holding a chart part

Everything else in the same `xl/drawings/drawingN.xml` — autoshapes, text boxes,
connectors, grouped shapes, SmartArt/diagram frames — has no openpyxl API and is
never seen by the parser, so it cannot reach an Element, an Anchor or the
renderer. Legacy `vmlDrawingN.vml` parts (form controls, comment boxes, older
shapes) are outside the DrawingML part entirely and are likewise invisible.

Charts are a separate case: they ARE perceived (an Element exists, with an
anchor) but the renderer draws a placeholder rather than the plotted chart,
because no chart-rendering engine is integrated.

The inventory below reports each kind with its actual visibility, so nothing is
described as rendered when it is not.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

_XDR_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_DGM_NS = "http://schemas.openxmlformats.org/drawingml/2006/diagram"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_SSML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


class Visibility:
    """How far an object gets through the pipeline."""
    RENDERED = "RENDERED"                # perceived and drawn
    PLACEHOLDER = "PLACEHOLDER"          # perceived, drawn as a stand-in only
    NOT_PERCEIVED = "NOT_PERCEIVED"      # never reaches an Element at all


# kind -> (display name, visibility, why)
KIND_SPEC: Dict[str, Dict[str, str]] = {
    "picture": {
        "display_name": "Pictures",
        "visibility": Visibility.RENDERED,
        "reason": "Read by openpyxl (ws._images) and drawn from the media endpoint.",
    },
    "chart": {
        "display_name": "Charts",
        "visibility": Visibility.PLACEHOLDER,
        "reason": ("Detected by openpyxl (ws._charts) and anchored, but drawn as a "
                   "placeholder — no chart-rendering engine is integrated."),
    },
    "shape": {
        "display_name": "Shapes",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": "openpyxl exposes no API for <xdr:sp>, so the parser never sees it.",
    },
    "text_box": {
        "display_name": "Text boxes",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": ("A text box is an <xdr:sp> carrying a <xdr:txBody>; openpyxl exposes "
                   "neither, so its text is not extracted."),
    },
    "connector": {
        "display_name": "Connectors",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": "openpyxl exposes no API for <xdr:cxnSp>.",
    },
    "group": {
        "display_name": "Grouped drawings",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": ("A group (<xdr:grpSp>) and everything nested inside it is skipped "
                   "wholesale by openpyxl."),
    },
    "diagram": {
        "display_name": "SmartArt / diagrams",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": ("A diagram is a <xdr:graphicFrame> holding a diagram part, not a "
                   "chart part, so it is not in ws._charts either."),
    },
    "graphic_frame_other": {
        "display_name": "Other embedded objects",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": "A graphic frame whose payload is neither a chart nor a diagram.",
    },
    "legacy_vml": {
        "display_name": "Legacy shapes / form controls",
        "visibility": Visibility.NOT_PERCEIVED,
        "reason": ("Stored in vmlDrawing parts outside DrawingML — form controls, "
                   "comment boxes and pre-2007 shapes. Not read at all."),
    },
}

# The kinds a viewer can legitimately claim to show completely.
_COMPLETE_KINDS = {"picture"}


@dataclass
class SheetVisualInventory:
    sheet_name: str
    counts: Dict[str, int] = field(default_factory=dict)
    pictures_read_by_parser: Optional[int] = None
    charts_read_by_parser: Optional[int] = None

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def unrendered_total(self) -> int:
        return sum(n for kind, n in self.counts.items() if kind not in _COMPLETE_KINDS)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_name": self.sheet_name,
            "total_objects": self.total,
            "unrendered_objects": self.unrendered_total,
            "pictures_read_by_parser": self.pictures_read_by_parser,
            "charts_read_by_parser": self.charts_read_by_parser,
            "objects": [
                {
                    "kind": kind,
                    "display_name": KIND_SPEC[kind]["display_name"],
                    "count": count,
                    "visibility": KIND_SPEC[kind]["visibility"],
                    "reason": KIND_SPEC[kind]["reason"],
                }
                for kind, count in sorted(self.counts.items())
                if count
            ],
        }


@dataclass
class WorkbookVisualInventory:
    filename: str
    sheets: List[SheetVisualInventory] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def totals(self) -> Dict[str, int]:
        totals: Dict[str, int] = {}
        for sheet in self.sheets:
            for kind, count in sheet.counts.items():
                totals[kind] = totals.get(kind, 0) + count
        return totals

    @property
    def has_visual_objects(self) -> bool:
        return any(sheet.total for sheet in self.sheets)

    @property
    def fully_rendered(self) -> bool:
        """False whenever the viewer would be showing an incomplete worksheet."""
        return all(kind in _COMPLETE_KINDS and count >= 0
                   for kind, count in self.totals.items() if count)

    def status_message(self) -> str:
        """One plain sentence for the UI. Never claims more than is true."""
        if self.error:
            return f"Visual objects could not be inspected: {self.error}"
        if not self.has_visual_objects:
            return "This workbook contains no drawing objects."
        if self.fully_rendered:
            return "Every drawing object in this workbook is shown."
        missing = {
            KIND_SPEC[kind]["display_name"].lower(): count
            for kind, count in self.totals.items()
            if count and kind not in _COMPLETE_KINDS
        }
        parts = ", ".join(f"{count} {name}" for name, count in sorted(missing.items()))
        return (f"This worksheet is not shown in full: {parts} are present in the file "
                f"but not drawn here.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "has_visual_objects": self.has_visual_objects,
            "fully_rendered": self.fully_rendered,
            "status_message": self.status_message(),
            "totals": {
                kind: {
                    "display_name": KIND_SPEC[kind]["display_name"],
                    "count": count,
                    "visibility": KIND_SPEC[kind]["visibility"],
                    "reason": KIND_SPEC[kind]["reason"],
                }
                for kind, count in sorted(self.totals.items()) if count
            },
            "sheets": [sheet.to_dict() for sheet in self.sheets],
            "error": self.error,
        }


# ============================================================================
# PACKAGE WALK
# ============================================================================

def _sheet_targets(archive: zipfile.ZipFile) -> List[tuple]:
    """[(sheet_name, worksheet_part_path)] in workbook order."""
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except KeyError:
        return []

    rel_targets = {
        rel.get("Id"): rel.get("Target", "")
        for rel in rels.findall(f"{{{_PKG_REL_NS}}}Relationship")
    }
    sheets = []
    for sheet in workbook.findall(f".//{{{_SSML_NS}}}sheet"):
        rel_id = sheet.get(f"{{{_R_NS}}}id")
        target = rel_targets.get(rel_id, "")
        if not target:
            continue
        part = target[1:] if target.startswith("/") else f"xl/{target.lstrip('./')}"
        sheets.append((sheet.get("name", "?"), part))
    return sheets


def _related_parts(archive: zipfile.ZipFile, part: str, pattern: str) -> List[str]:
    rels_path = f"{Path(part).parent.as_posix()}/_rels/{Path(part).name}.rels"
    try:
        rels = ET.fromstring(archive.read(rels_path))
    except KeyError:
        return []
    out = []
    for rel in rels.findall(f"{{{_PKG_REL_NS}}}Relationship"):
        target = rel.get("Target", "")
        if not re.search(pattern, target):
            continue
        if target.startswith("/"):
            out.append(target[1:])
        else:
            out.append((Path(part).parent / target).as_posix().replace("/./", "/"))
    return [re.sub(r"[^/]+/\.\./", "", p) for p in out]


def _classify_drawing(archive: zipfile.ZipFile, drawing_part: str) -> Dict[str, int]:
    """Counts every anchored object in one drawing part, groups included."""
    counts: Dict[str, int] = {}
    try:
        root = ET.fromstring(archive.read(drawing_part))
    except (KeyError, ET.ParseError):
        return counts

    def bump(kind: str) -> None:
        counts[kind] = counts.get(kind, 0) + 1

    def walk(node) -> None:
        for child in node:
            tag = child.tag
            if tag == f"{{{_XDR_NS}}}pic":
                bump("picture")
            elif tag == f"{{{_XDR_NS}}}sp":
                has_text = child.find(f".//{{{_XDR_NS}}}txBody") is not None
                bump("text_box" if has_text else "shape")
            elif tag == f"{{{_XDR_NS}}}cxnSp":
                bump("connector")
            elif tag == f"{{{_XDR_NS}}}grpSp":
                bump("group")
                walk(child)  # nested members are counted too, none are rendered
                continue
            elif tag == f"{{{_XDR_NS}}}graphicFrame":
                if child.find(f".//{{{_C_NS}}}chart") is not None:
                    bump("chart")
                elif child.find(f".//{{{_DGM_NS}}}relIds") is not None:
                    bump("diagram")
                else:
                    bump("graphic_frame_other")
            else:
                walk(child)

    walk(root)
    return counts


def inventory_xlsx_visual_objects(path: str,
                                  parser_counts: Optional[Dict[str, Dict[str, int]]] = None
                                  ) -> WorkbookVisualInventory:
    """Inventories every drawing object in a workbook, per sheet.

    `parser_counts` optionally carries what the perception pipeline actually
    read, as {sheet_name: {"images": n, "charts": n}}, so the report can show the
    gap between what the file holds and what was perceived.
    """
    inventory = WorkbookVisualInventory(filename=Path(path).name)
    parser_counts = parser_counts or {}

    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for sheet_name, part in _sheet_targets(archive):
                sheet = SheetVisualInventory(sheet_name=sheet_name)

                for drawing_part in _related_parts(archive, part, r"drawing\d*\.xml$"):
                    if drawing_part in names:
                        for kind, count in _classify_drawing(archive, drawing_part).items():
                            sheet.counts[kind] = sheet.counts.get(kind, 0) + count

                for vml_part in _related_parts(archive, part, r"vmlDrawing\d*\.vml$"):
                    if vml_part not in names:
                        continue
                    try:
                        shapes = len(re.findall(rb"<v:shape\b", archive.read(vml_part)))
                    except KeyError:
                        shapes = 0
                    if shapes:
                        sheet.counts["legacy_vml"] = sheet.counts.get("legacy_vml", 0) + shapes

                seen = parser_counts.get(sheet_name)
                if seen:
                    sheet.pictures_read_by_parser = seen.get("images")
                    sheet.charts_read_by_parser = seen.get("charts")

                inventory.sheets.append(sheet)
    except (zipfile.BadZipFile, OSError) as exc:
        inventory.error = str(exc)

    return inventory


def parser_visual_counts(path: str) -> Dict[str, Dict[str, int]]:
    """What the current perception pipeline actually reads, per sheet.

    Read-only: it opens the workbook exactly the way parser.py does and reports
    the two collections openpyxl exposes. It changes no perception semantics.
    """
    import openpyxl

    counts: Dict[str, Dict[str, int]] = {}
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=False)
    try:
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            counts[sheet_name] = {
                "images": len(getattr(worksheet, "_images", []) or []),
                "charts": len(getattr(worksheet, "_charts", []) or []),
            }
    finally:
        workbook.close()
    return counts


def audit_workbook(path: str) -> Dict[str, Any]:
    """The full report: what the file holds, and what the pipeline sees."""
    try:
        seen = parser_visual_counts(path)
    except Exception:
        seen = {}
    return inventory_xlsx_visual_objects(path, parser_counts=seen).to_dict()


__all__ = [
    "Visibility",
    "KIND_SPEC",
    "SheetVisualInventory",
    "WorkbookVisualInventory",
    "inventory_xlsx_visual_objects",
    "parser_visual_counts",
    "audit_workbook",
]

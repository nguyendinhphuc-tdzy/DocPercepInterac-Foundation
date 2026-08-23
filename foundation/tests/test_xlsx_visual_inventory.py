"""
XLSX visual-object inventory (Phase PROD-UX-1, audit only).

The inventory exists so the viewer can state that a worksheet is incomplete.
These tests pin the two things that makes true:
    * every drawing kind is classified, including members nested in groups and
      legacy VML parts openpyxl never touches
    * a workbook holding anything the renderer cannot draw is reported as NOT
      fully rendered, with a reason per kind
"""
from __future__ import annotations

import warnings
import zipfile
from pathlib import Path

import pytest

from perception.xlsx_visual_inventory import (
    KIND_SPEC,
    Visibility,
    _classify_drawing,
    audit_workbook,
    inventory_xlsx_visual_objects,
    parser_visual_counts,
)

warnings.filterwarnings("ignore")

DEMO = Path(__file__).resolve().parents[2] / "anonymize client" / "Demo files" / "Demo files"
APPENDIX_I = (DEMO / "FA&RPTS & Appendix I" / "Appendix I"
              / "HMV-25-Appendix I under D20 for FY2024-Final-W3103.xlsx")
FA_RPT = DEMO / "FA&RPTS & Appendix I" / "FA&RPTs" / "HMV-FA&RPT FY2024.xlsx"

XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
DGM = "http://schemas.openxmlformats.org/drawingml/2006/diagram"

SYNTHETIC_DRAWING = f"""<?xml version="1.0"?>
<xdr:wsDr xmlns:xdr="{XDR}" xmlns:c="{C}" xmlns:dgm="{DGM}">
  <xdr:twoCellAnchor><xdr:pic/></xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:sp macro="" textlink=""/></xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:sp macro=""><xdr:txBody/></xdr:sp></xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:cxnSp macro=""/></xdr:twoCellAnchor>
  <xdr:twoCellAnchor>
    <xdr:grpSp><xdr:sp/><xdr:pic/></xdr:grpSp>
  </xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:graphicFrame><c:chart/></xdr:graphicFrame></xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:graphicFrame><dgm:relIds/></xdr:graphicFrame></xdr:twoCellAnchor>
  <xdr:twoCellAnchor><xdr:graphicFrame/></xdr:twoCellAnchor>
</xdr:wsDr>
"""


@pytest.fixture
def synthetic_archive(tmp_path) -> zipfile.ZipFile:
    path = tmp_path / "drawings.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/drawings/drawing1.xml", SYNTHETIC_DRAWING)
    return zipfile.ZipFile(path)


# ---------------------------------------------------------------------------
# CLASSIFICATION
# ---------------------------------------------------------------------------

def test_every_drawing_kind_is_classified(synthetic_archive):
    counts = _classify_drawing(synthetic_archive, "xl/drawings/drawing1.xml")

    assert counts["picture"] == 2          # one top-level, one inside the group
    assert counts["shape"] == 2            # one top-level, one inside the group
    assert counts["text_box"] == 1         # an <xdr:sp> carrying a <xdr:txBody>
    assert counts["connector"] == 1
    assert counts["group"] == 1
    assert counts["chart"] == 1
    assert counts["diagram"] == 1
    assert counts["graphic_frame_other"] == 1


def test_group_members_are_counted_not_skipped(synthetic_archive):
    counts = _classify_drawing(synthetic_archive, "xl/drawings/drawing1.xml")
    # The group itself plus both of its members are accounted for; openpyxl sees
    # none of the three, which is the whole point of counting them here.
    assert counts["group"] == 1
    assert counts["picture"] + counts["shape"] == 4


def test_only_pictures_claim_to_be_rendered():
    rendered = {kind for kind, spec in KIND_SPEC.items()
                if spec["visibility"] == Visibility.RENDERED}
    assert rendered == {"picture"}
    assert KIND_SPEC["chart"]["visibility"] == Visibility.PLACEHOLDER
    assert all(KIND_SPEC[kind]["reason"] for kind in KIND_SPEC)


# ---------------------------------------------------------------------------
# REAL WORKBOOKS
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not APPENDIX_I.exists(), reason="demo fixtures are not present")
def test_appendix_i_inventory_matches_its_package():
    report = audit_workbook(str(APPENDIX_I))
    totals = {kind: entry["count"] for kind, entry in report["totals"].items()}

    assert totals == {"picture": 4, "shape": 12, "connector": 2, "group": 2, "legacy_vml": 12}
    assert report["fully_rendered"] is False
    assert "not shown in full" in report["status_message"]


@pytest.mark.skipif(not FA_RPT.exists(), reason="demo fixtures are not present")
def test_report_shows_the_gap_between_file_and_parser():
    inventory = inventory_xlsx_visual_objects(
        str(FA_RPT), parser_counts=parser_visual_counts(str(FA_RPT)))

    gaps = [sheet for sheet in inventory.sheets
            if sheet.total and (sheet.pictures_read_by_parser or 0) < sheet.total]
    assert gaps, "at least one sheet holds more objects than the parser read"
    for sheet in gaps:
        assert sheet.pictures_read_by_parser is not None  # the comparison is real, not assumed


@pytest.mark.skipif(not FA_RPT.exists(), reason="demo fixtures are not present")
def test_status_message_never_overstates_what_is_drawn():
    report = audit_workbook(str(FA_RPT))
    assert "Every drawing object" not in report["status_message"]
    for entry in report["totals"].values():
        if entry["visibility"] != Visibility.RENDERED:
            assert entry["display_name"].lower() in report["status_message"].lower()


def test_a_workbook_without_drawings_is_reported_as_complete(tmp_path):
    import openpyxl

    path = tmp_path / "plain.xlsx"
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = "value"
    workbook.save(path)

    report = audit_workbook(str(path))
    assert report["has_visual_objects"] is False
    assert report["fully_rendered"] is True
    assert report["status_message"] == "This workbook contains no drawing objects."


def test_a_corrupt_file_reports_an_error_instead_of_raising(tmp_path):
    path = tmp_path / "broken.xlsx"
    path.write_bytes(b"not a zip")

    report = audit_workbook(str(path))
    assert report["error"]
    assert "could not be inspected" in report["status_message"]

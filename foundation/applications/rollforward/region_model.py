"""
Canonical Roll-Forward Region Model (Phase F)
==============================================
Location: foundation/applications/rollforward/region_model.py

Resolves the 61 vs 81 region discrepancy with document evidence.

What the three numbers actually were
------------------------------------
    104  Phase B/C `TemplateRegionSegmenter` element-block segmentation.
         Over-counts: its heading regex matches `toc 1` / `toc 2` paragraphs
         ("PART A. TAXPAYER INFORMATION<tab>4"), so table-of-contents lines
         became sections, and one section could yield several regions.

     81  NOT PRODUCED BY ANY CODE. It appears only in the prose of
         `LocalFile_RollForward_Template_Profile_2026-08-21.md`, and is
         contradicted by the JSON emitted by that same run, which records 104.
         It is an authoring error in a report already marked
         INVALIDATED_FOR_PLANNING_CONTAMINATION.

     61  Phase E heading-delimited segmentation. Correct method, incomplete
         style set: it matched `Heading 1..4` / `Title` / `Subtitle` but not the
         template's `Appendix Heading`, `Appendix Heading 2` and
         `Appendix Heading 3` styles, which carry 17 real headings.

The canonical answer
--------------------
    ELEMENT     848   perception blocks
    SUBREGION    16   tables  +  38 drawing constructs
    REGION       94   section body, plus one region per contained table
    SECTION      78   77 headings (Heading 1-4 + Appendix Heading 1-3) + preamble
    DOCUMENT      1

Neither 61 nor 81 is correct. This module states the corrected counts and the
rule that produces them; it does not rename or silently merge anything.

No mutation. No Ground Truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from docx import Document
from docx.text.paragraph import Paragraph

# Styles that open a SECTION. The appendix band is part of the template's real
# outline; excluding it was the Phase E undercount.
HEADING_STYLE_RE = re.compile(
    r"^(heading\s*(\d+)|appendix\s+heading(\s*(\d+))?|title|subtitle)$", re.IGNORECASE)

# Table-of-contents styles. These LOOK like headings (same words, plus a page
# number) and must never open a section. Counting them was the Phase B/C
# overcount.
TOC_STYLE_RE = re.compile(r"^toc\s*\d*$", re.IGNORECASE)

# Appendix headings sort after the main body outline.
APPENDIX_LEVEL_OFFSET = 10


class NodeKind(str, Enum):
    DOCUMENT = "DOCUMENT"
    SECTION = "SECTION"
    REGION = "REGION"
    SUBREGION = "SUBREGION"
    ELEMENT = "ELEMENT"


class SubregionKind(str, Enum):
    TABLE = "TABLE"
    FIGURE = "FIGURE"
    NARRATIVE_BLOCK = "NARRATIVE_BLOCK"


@dataclass
class Subregion:
    subregion_id: str
    kind: SubregionKind
    ordinal: Optional[int] = None            # table ordinal within the document
    paragraph_index: Optional[int] = None    # figure anchor paragraph
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"subregion_id": self.subregion_id, "kind": self.kind.value,
                "ordinal": self.ordinal, "paragraph_index": self.paragraph_index,
                "label": self.label}


@dataclass
class Region:
    """An executable unit: a narrative body block or a single table."""
    region_id: str
    section_id: str
    kind: SubregionKind
    paragraph_indices: List[int] = field(default_factory=list)
    table_ordinal: Optional[int] = None
    subregions: List[Subregion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"region_id": self.region_id, "section_id": self.section_id,
                "kind": self.kind.value, "paragraph_indices": self.paragraph_indices,
                "table_ordinal": self.table_ordinal,
                "subregions": [s.to_dict() for s in self.subregions]}


@dataclass
class Section:
    """A heading-delimited part of the document outline."""
    section_id: str
    heading: str
    heading_style: str
    level: int
    is_appendix: bool
    section_path: List[str]
    paragraph_indices: List[int] = field(default_factory=list)
    table_ordinals: List[int] = field(default_factory=list)
    figure_paragraphs: List[int] = field(default_factory=list)
    region_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"section_id": self.section_id, "heading": self.heading,
                "heading_style": self.heading_style, "level": self.level,
                "is_appendix": self.is_appendix, "section_path": self.section_path,
                "paragraph_count": len(self.paragraph_indices),
                "table_ordinals": self.table_ordinals,
                "figure_paragraphs": self.figure_paragraphs,
                "region_ids": self.region_ids}


@dataclass
class DocumentRegionModel:
    """The canonical Document -> Section -> Region -> Subregion -> Element tree."""
    document_name: str
    sections: List[Section]
    regions: List[Region]
    subregions: List[Subregion]
    element_count: int
    body_paragraph_count: int
    body_table_count: int
    figure_paragraph_count: int
    toc_paragraphs_excluded: int
    heading_style_histogram: Dict[str, int]

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "DOCUMENT": 1,
            "SECTION": len(self.sections),
            "REGION": len(self.regions),
            "SUBREGION": len(self.subregions),
            "ELEMENT": self.element_count,
        }

    def is_exact_partition(self) -> bool:
        """Every body paragraph and table belongs to exactly one section and region."""
        s_paras = [p for s in self.sections for p in s.paragraph_indices]
        s_tables = [t for s in self.sections for t in s.table_ordinals]
        r_paras = [p for r in self.regions for p in r.paragraph_indices]
        r_tables = [r.table_ordinal for r in self.regions if r.table_ordinal is not None]
        return (
            len(s_paras) == len(set(s_paras)) == self.body_paragraph_count
            and len(s_tables) == len(set(s_tables)) == self.body_table_count
            and len(r_paras) == len(set(r_paras)) == self.body_paragraph_count
            and len(r_tables) == len(set(r_tables)) == self.body_table_count
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_name": self.document_name,
            "counts": self.counts,
            "is_exact_partition": self.is_exact_partition(),
            "body_paragraph_count": self.body_paragraph_count,
            "body_table_count": self.body_table_count,
            "figure_paragraph_count": self.figure_paragraph_count,
            "toc_paragraphs_excluded": self.toc_paragraphs_excluded,
            "heading_style_histogram": self.heading_style_histogram,
            "sections": [s.to_dict() for s in self.sections],
            "regions": [r.to_dict() for r in self.regions],
        }


class CanonicalRegionModelBuilder:
    """Builds the canonical hierarchy from a DOCX using document evidence only."""

    _W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    @classmethod
    def build(cls, doc_path: Path, element_count: Optional[int] = None) -> DocumentRegionModel:
        doc = Document(str(doc_path))
        sections: List[Section] = []
        regions: List[Region] = []
        subregions: List[Subregion] = []
        histogram: Dict[str, int] = {}
        stack: List[Tuple[int, str]] = []
        toc_excluded = 0
        p_idx = t_idx = 0
        fig_paragraphs: List[int] = []

        def new_section(heading: str, style: str, level: int, is_appendix: bool) -> Section:
            return Section(
                section_id=f"sec-{len(sections) + 1:03d}", heading=heading,
                heading_style=style, level=level, is_appendix=is_appendix,
                section_path=[h for _, h in stack])

        current = new_section("PREAMBLE (before first heading)", "", 0, False)

        for child in doc.element.body:
            tag = child.tag.split("}")[-1]
            if tag == "p":
                p = Paragraph(child, doc)
                p_idx += 1
                style = (p.style.name if p.style else "").strip()
                text = re.sub(r"\s+", " ", p.text or "").strip()

                if TOC_STYLE_RE.match(style):
                    # A table-of-contents line, never a section opener.
                    toc_excluded += 1
                elif HEADING_STYLE_RE.match(style) and text:
                    histogram[style] = histogram.get(style, 0) + 1
                    digits = re.findall(r"\d+", style)
                    level = int(digits[0]) if digits else 1
                    is_appendix = style.lower().startswith("appendix")
                    if is_appendix:
                        level += APPENDIX_LEVEL_OFFSET
                    while stack and stack[-1][0] >= level:
                        stack.pop()
                    sections.append(current)
                    stack.append((level, text))
                    current = new_section(text, style, level, is_appendix)
                    current.section_path = [h for _, h in stack[:-1]]

                current.paragraph_indices.append(p_idx)
                if cls._is_figure_paragraph(child):
                    current.figure_paragraphs.append(p_idx)
                    fig_paragraphs.append(p_idx)
            elif tag == "tbl":
                current.table_ordinals.append(t_idx)
                t_idx += 1

        sections.append(current)

        # ---- REGION layer: narrative body + one region per contained table ----
        for section in sections:
            body = Region(
                region_id=f"rgn-{len(regions) + 1:03d}", section_id=section.section_id,
                kind=SubregionKind.NARRATIVE_BLOCK,
                paragraph_indices=list(section.paragraph_indices))
            for fp in section.figure_paragraphs:
                sub = Subregion(subregion_id=f"sub-fig-p{fp:04d}", kind=SubregionKind.FIGURE,
                                paragraph_index=fp, label=f"figure at paragraph {fp}")
                body.subregions.append(sub)
                subregions.append(sub)
            regions.append(body)
            section.region_ids.append(body.region_id)

            for ordinal in section.table_ordinals:
                sub = Subregion(subregion_id=f"sub-tbl-{ordinal:03d}", kind=SubregionKind.TABLE,
                                ordinal=ordinal, label=f"table {ordinal}")
                subregions.append(sub)
                tbl_region = Region(
                    region_id=f"rgn-{len(regions) + 1:03d}", section_id=section.section_id,
                    kind=SubregionKind.TABLE, table_ordinal=ordinal, subregions=[sub])
                regions.append(tbl_region)
                section.region_ids.append(tbl_region.region_id)

        return DocumentRegionModel(
            document_name=doc_path.name, sections=sections, regions=regions,
            subregions=subregions,
            element_count=element_count if element_count is not None else 0,
            body_paragraph_count=p_idx, body_table_count=t_idx,
            figure_paragraph_count=len(fig_paragraphs),
            toc_paragraphs_excluded=toc_excluded,
            heading_style_histogram=histogram)

    @classmethod
    def _is_figure_paragraph(cls, child: Any) -> bool:
        return bool(child.findall(f".//{cls._W}drawing")) or bool(
            child.findall(f".//{cls._W}pict")) or any(
            n.tag.endswith("}graphicData") for n in child.iter())


# ============================================================================
# DISCREPANCY RECORD
# ============================================================================

@dataclass(frozen=True)
class RegionCountClaim:
    """A historical region count, with what produced it and whether it holds."""
    value: int
    claimed_by: str
    produced_by: str
    verdict: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def region_count_reconciliation(model: DocumentRegionModel) -> Dict[str, Any]:
    """The formal 61 / 81 / 104 resolution, measured against the live template."""
    hist = model.heading_style_histogram
    main = sum(n for s, n in hist.items() if not s.lower().startswith("appendix"))
    appendix = sum(n for s, n in hist.items() if s.lower().startswith("appendix"))

    claims = [
        RegionCountClaim(
            value=61, claimed_by="Phase E source-completeness audit",
            produced_by="heading-delimited segmentation over Heading 1-4 / Title / Subtitle",
            verdict="UNDERCOUNT — correct method, incomplete style set",
            explanation=(
                f"It matched the {main} main-outline headings but not the {appendix} "
                f"`Appendix Heading` / `Appendix Heading 2` / `Appendix Heading 3` paragraphs, "
                f"which are real headings in this template. {main} + 1 preamble = 61.")),
        RegionCountClaim(
            value=81, claimed_by="Phase B template profile report (markdown prose)",
            produced_by="nothing — no code path produces 81",
            verdict="UNSUPPORTED — contradicted by its own run's JSON",
            explanation=(
                "The same profiling run wrote 104 into "
                "`LocalFile_RollForward_Template_Profile_2026-08-21.json` "
                "(`statistics.total_regions`). The figure 81 appears only in the report prose, "
                "in a document already marked INVALIDATED_FOR_PLANNING_CONTAMINATION.")),
        RegionCountClaim(
            value=104, claimed_by="Phase B/C manifest and template profile JSON",
            produced_by="TemplateRegionSegmenter element-block segmentation",
            verdict="OVERCOUNT — table-of-contents lines counted as sections",
            explanation=(
                f"Its heading test accepted `toc 1` / `toc 2` paragraphs such as "
                f"'PART A. TAXPAYER INFORMATION<tab>4', which are contents entries carrying a "
                f"page number. This template holds {model.toc_paragraphs_excluded} such "
                f"paragraphs. It also emitted several regions per section.")),
    ]

    return {
        "question": "Is 61 the count of semantic Sections and 81 the count of executable Regions?",
        "answer": "NO. Neither figure is correct, and they are not two layers of one hierarchy.",
        "canonical_counts": model.counts,
        "canonical_rule": {
            "section_opens_on": "Heading 1-4, Title, Subtitle, Appendix Heading 1-3",
            "never_opens_on": "toc 1 / toc 2 (table-of-contents lines)",
            "region_rule": "one narrative-body region per section, plus one region per "
                           "contained table",
            "subregion_rule": "tables and figures",
            "element_rule": "Foundation perception blocks",
        },
        "heading_style_histogram": hist,
        "main_outline_headings": main,
        "appendix_headings": appendix,
        "toc_paragraphs_excluded": model.toc_paragraphs_excluded,
        "claims": [c.to_dict() for c in claims],
        "is_exact_partition": model.is_exact_partition(),
        "note": ("No region was renamed or merged. The historical counts are recorded above "
                 "with the code that produced them; the canonical model is stated separately."),
    }

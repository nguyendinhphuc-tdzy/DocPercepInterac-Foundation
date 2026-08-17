"""Comparison harness for the document-level `Classifier` seam
(perception/element_classifier.py).

Purpose: once a user plugs in an AI-backed `Classifier` to replace or
compare against the deterministic baseline (`classify_blocks`), they need a
way to see how much the two agree before trusting the new one. This module
runs two Classifiers on the SAME extracted blocks/anchors and reports
agreement + a list of concrete divergences — independent of, and never
touched by, the mapping pipeline (applications/gpts/) or any other
use-case-specific code.

Import boundary: this module imports ONLY from `perception.*` (plus
stdlib). No `applications/`, `mapping/`, or `gpts` — the harness must stay
usable for any document/use case, not just the GTPS demo.

IMPORTANT — this measures AGREEMENT WITH THE BASELINE, NOT accuracy. The
baseline (`classify_blocks`) is a rough, deterministic stand-in (style_id
prefix / presence of table_index), not ground truth. A good AI classifier
might INTENTIONALLY diverge from it — e.g. assigning a more precise
ElementType, or a section-aware name a per-block heuristic could never
produce. Low agreement is not automatically a regression: inspect
`divergences` and judge case by case whether each one is an improvement or
a mistake.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perception.anchor_builder import assign_anchors  # noqa: E402
from perception.element_classifier import Classifier, classify_blocks  # noqa: E402
from perception.models import Anchor, Element, ElementType  # noqa: E402
from perception.parser import extract_geometry  # noqa: E402


@dataclass
class Divergence:
    """One element where baseline and candidate disagree (index present in
    both). Only covers dimensions the Classifier is responsible for:
    ElementType, display name, and whether the anchor it was handed was
    preserved unchanged."""

    index: int
    baseline_type: ElementType
    candidate_type: ElementType
    baseline_name: str
    candidate_name: str
    anchor_changed: bool


@dataclass
class ComparisonReport:
    """Result of comparing a candidate Classifier's output against the
    baseline's, element-by-element (matched by `Element.index`).

    Every ratio here is AGREEMENT WITH THE BASELINE, NOT "accuracy" — the
    baseline is a rough deterministic starting point, not ground truth. A
    good candidate classifier may deliberately diverge (finer-grained
    types, context-aware section names a per-block heuristic can't
    produce). Use `divergences` to judge, case by case, whether each
    disagreement is an improvement or a genuine error — a low agreement
    score alone does not mean the candidate is wrong.
    """

    total_elements: int  # len(baseline)
    count_match: bool  # len(baseline) == len(candidate)
    # Ratios over indices present in BOTH baseline and candidate (0 if none).
    type_agreement: float
    name_agreement: float
    anchor_preserved: float
    exact_agreement: float
    divergences: list[Divergence] = field(default_factory=list)
    missing_in_candidate: list[int] = field(default_factory=list)  # in baseline only
    extra_in_candidate: list[int] = field(default_factory=list)  # in candidate only


def diff_elements(baseline: list[Element], candidate: list[Element]) -> ComparisonReport:
    """Pure function — no I/O. Compares two already-produced Element lists,
    matching them up by `Element.index` (not list position, so a
    misbehaving candidate that skips/renumbers elements is still handled
    sanely rather than silently misaligning the comparison).

    A correct Classifier must hand back the EXACT Anchor it was given for
    each block, unchanged (anchor assignment is a separate, earlier step —
    perception/anchor_builder.py — the Classifier only labels blocks, it
    never re-derives their anchor). Anchors are therefore compared with
    plain `==`.
    """
    baseline_by_index = {el.index: el for el in baseline}
    candidate_by_index = {el.index: el for el in candidate}

    common = sorted(set(baseline_by_index) & set(candidate_by_index))
    missing_in_candidate = sorted(set(baseline_by_index) - set(candidate_by_index))
    extra_in_candidate = sorted(set(candidate_by_index) - set(baseline_by_index))

    divergences: list[Divergence] = []
    type_matches = 0
    name_matches = 0
    anchor_matches = 0
    exact_matches = 0

    for idx in common:
        b = baseline_by_index[idx]
        c = candidate_by_index[idx]
        type_match = b.type == c.type
        name_match = b.name == c.name
        anchor_match = b.anchor == c.anchor

        type_matches += type_match
        name_matches += name_match
        anchor_matches += anchor_match

        if type_match and name_match and anchor_match:
            exact_matches += 1
        else:
            divergences.append(
                Divergence(
                    index=idx,
                    baseline_type=b.type,
                    candidate_type=c.type,
                    baseline_name=b.name,
                    candidate_name=c.name,
                    anchor_changed=not anchor_match,
                )
            )

    denom = len(common)

    def ratio(n: int) -> float:
        return n / denom if denom else 0.0

    return ComparisonReport(
        total_elements=len(baseline),
        count_match=len(baseline) == len(candidate),
        type_agreement=ratio(type_matches),
        name_agreement=ratio(name_matches),
        anchor_preserved=ratio(anchor_matches),
        exact_agreement=ratio(exact_matches),
        divergences=divergences,
        missing_in_candidate=missing_in_candidate,
        extra_in_candidate=extra_in_candidate,
    )


def compare_on_document(
    path: str,
    candidate: Classifier,
    baseline: Classifier = classify_blocks,
) -> ComparisonReport:
    """End-to-end: extract geometry once, assign anchors once, then run
    BOTH the baseline and the candidate Classifier on that identical
    (blocks, fmt, anchors) input — so any difference in their output is
    attributable to classification alone, never to different inputs — and
    diff the results.
    """
    blocks = extract_geometry(path)
    fmt = Path(path).suffix.lower().lstrip(".")
    anchors = assign_anchors(blocks, fmt)

    baseline_elements = baseline(blocks, fmt, anchors)
    candidate_elements = candidate(blocks, fmt, anchors)

    return diff_elements(baseline_elements, candidate_elements)


_MAX_DIVERGENCE_LINES = 50


def render_report(report: ComparisonReport) -> str:
    """Human-readable rendering of a ComparisonReport: a concise metrics
    summary followed by a (possibly truncated) list of divergences."""
    lines = [
        "Classifier comparison report — agreement with baseline, NOT accuracy",
        "=" * 72,
        f"total_elements (baseline) : {report.total_elements}",
        f"count_match                : {report.count_match}",
        f"type_agreement             : {report.type_agreement:.1%}",
        f"name_agreement              : {report.name_agreement:.1%}",
        f"anchor_preserved            : {report.anchor_preserved:.1%}",
        f"exact_agreement             : {report.exact_agreement:.1%}",
    ]
    if report.missing_in_candidate:
        lines.append(f"missing_in_candidate       : {report.missing_in_candidate}")
    if report.extra_in_candidate:
        lines.append(f"extra_in_candidate         : {report.extra_in_candidate}")

    lines.append("")
    if not report.divergences:
        lines.append("No divergences.")
    else:
        lines.append(f"Divergences ({len(report.divergences)}):")
        for d in report.divergences[:_MAX_DIVERGENCE_LINES]:
            lines.append(
                f"  [{d.index}] type: {d.baseline_type.value} -> {d.candidate_type.value}"
                f" | name: {d.baseline_name!r} -> {d.candidate_name!r}"
                f" | anchor_changed: {d.anchor_changed}"
            )
        remaining = len(report.divergences) - _MAX_DIVERGENCE_LINES
        if remaining > 0:
            lines.append(f"... and {remaining} more")

    return "\n".join(lines)


# TODO: REPLACE with a wrapper around your model. The model must accept
# (blocks, fmt, anchors, start_index) and return a list[Element] of the
# same order/length, PRESERVING the provided anchor for each block.
def candidate_stub(
    blocks: list[Mapping[str, Any]],
    fmt: str,
    anchors: list[Anchor],
    start_index: int = 0,
) -> list[Element]:
    """Placeholder `Classifier` — no AI model exists yet. Currently just
    delegates to the deterministic baseline (`classify_blocks`) so this
    harness runs today and produces a 100% agreement report: a sanity
    check that the harness itself introduces no false diffs, before any
    real model is plugged in here.
    """
    return classify_blocks(blocks, fmt, anchors, start_index=start_index)


if __name__ == "__main__":
    fixture_path = (
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "fixture_generic_handbook.docx"
    )
    result = compare_on_document(str(fixture_path), candidate_stub)
    print(render_report(result))
